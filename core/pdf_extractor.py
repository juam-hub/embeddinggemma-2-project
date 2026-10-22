import re
import pymupdf  # PyMuPDF
from pathlib import Path
from typing import List, Dict, Any, Callable, Optional
from PIL import Image
from core.config import (
    EXTRACTED_IMAGES_DIR,
    MIN_IMAGE_WIDTH,
    MIN_IMAGE_HEIGHT,
    CHUNK_SIZE,
    CHUNK_OVERLAP
)

def sanitize_filename(name: str) -> str:
    return re.sub(r'[^a-zA-Z0-9_\-]', '_', name)

def chunk_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> List[str]:
    """
    Semantically chunks text by paragraphs or sentences with overlap.
    """
    text = text.strip()
    if not text:
        return []

    # If text is shorter than chunk_size, return as single chunk
    if len(text) <= chunk_size:
        return [text]

    paragraphs = text.split("\n\n")
    chunks = []
    current_chunk = ""

    for para in paragraphs:
        para = para.strip()
        if not para:
            continue
        
        # If adding this paragraph exceeds chunk_size, store current and start new
        if len(current_chunk) + len(para) + 2 > chunk_size and current_chunk:
            chunks.append(current_chunk.strip())
            # Overlap: keep the last portion of current_chunk
            overlap_text = current_chunk[-overlap:] if len(current_chunk) > overlap else current_chunk
            current_chunk = overlap_text + "\n\n" + para
        else:
            if current_chunk:
                current_chunk += "\n\n" + para
            else:
                current_chunk = para

    if current_chunk.strip():
        chunks.append(current_chunk.strip())

    return chunks

class PDFExtractor:
    def __init__(self, output_dir: Path = EXTRACTED_IMAGES_DIR):
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def process_pdf(
        self,
        pdf_path: Path,
        progress_callback: Optional[Callable[[int, int, str], None]] = None
    ) -> Dict[str, Any]:
        """
        Processes a PDF document:
        - Extracts text per page and chunks it with page number metadata.
        - Extracts embedded images and vector graphics (charts/diagrams) filtered by size.
        """
        pdf_path = Path(pdf_path)
        safe_name = sanitize_filename(pdf_path.stem)
        doc = pymupdf.open(str(pdf_path))
        total_pages = len(doc)

        all_text_chunks: List[Dict[str, Any]] = []
        all_visual_elements: List[Dict[str, Any]] = []
        seen_image_hashes = set()

        for page_idx in range(total_pages):
            page_num = page_idx + 1
            page = doc[page_idx]

            if progress_callback:
                progress_callback(page_num, total_pages, f"Analizando página {page_num} de {total_pages}...")

            # 1. Extract and chunk text
            page_text = page.get_text("text")
            chunks = chunk_text(page_text)
            for c_idx, chunk in enumerate(chunks):
                all_text_chunks.append({
                    "chunk_id": f"{safe_name}_p{page_num}_c{c_idx+1}",
                    "doc_name": pdf_path.name,
                    "page_number": page_num,
                    "content": chunk,
                    "source_type": "text"
                })

            # 2. Extract embedded raster images
            image_list = page.get_images(full=True)

            for img_idx, img_info in enumerate(image_list):
                xref = img_info[0]
                base_image = doc.extract_image(xref)
                if not base_image:
                    continue

                width = base_image.get("width", 0)
                height = base_image.get("height", 0)

                # Filter by dimensions
                if width < MIN_IMAGE_WIDTH or height < MIN_IMAGE_HEIGHT:
                    continue

                image_bytes = base_image["image"]

                # De-duplicate identical image bytes across pages
                img_hash = hash(image_bytes)
                if img_hash in seen_image_hashes:
                    continue
                seen_image_hashes.add(img_hash)

                elem_id = f"{safe_name}_p{page_num}_img{img_idx+1}"
                img_filename = f"{elem_id}.png"
                img_filepath = self.output_dir / img_filename

                # Save as standard PNG
                try:
                    pix = pymupdf.Pixmap(doc, xref)
                    if pix.n >= 5:  # CMYK or other color space
                        pix = pymupdf.Pixmap(pymupdf.csRGB, pix)
                    pix.save(str(img_filepath))
                    pix = None
                except Exception:
                    # Fallback write raw bytes
                    with open(img_filepath, "wb") as f:
                        f.write(image_bytes)

                # Performance optimization: normalize max dimension to 1024px to save disk and memory
                try:
                    with Image.open(img_filepath) as im:
                        if im.width > 1024 or im.height > 1024:
                            im_copy = im.copy()
                            im_copy.thumbnail((1024, 1024), Image.Resampling.LANCZOS)
                            im_copy.save(img_filepath, format="PNG", optimize=True)
                            width, height = im_copy.size
                except Exception:
                    pass

                # Track visual element
                all_visual_elements.append({
                    "element_id": elem_id,
                    "doc_name": pdf_path.name,
                    "page_number": page_num,
                    "element_type": "embedded_image",
                    "image_path": str(img_filepath),
                    "width": width,
                    "height": height
                })

            # 3. Detect and extract vector drawings / charts (e.g. matplotlib/excel/flowcharts)
            try:
                drawings = page.get_drawings()
                if len(drawings) >= 8:  # meaningful vector complexity
                    combined_rect = None
                    for d in drawings:
                        rect = d["rect"]
                        if rect.width > page.rect.width * 0.95 and rect.height > page.rect.height * 0.95:
                            continue
                        if combined_rect is None:
                            combined_rect = pymupdf.Rect(rect)
                        else:
                            combined_rect |= rect

                    if combined_rect and combined_rect.is_valid and not combined_rect.is_empty:
                        w = int(combined_rect.width)
                        h = int(combined_rect.height)
                        if w >= MIN_IMAGE_WIDTH and h >= MIN_IMAGE_HEIGHT:
                            elem_id = f"{safe_name}_p{page_num}_drawing1"
                            img_filename = f"{elem_id}.png"
                            img_filepath = self.output_dir / img_filename
                            
                            clip_rect = pymupdf.Rect(
                                max(0, combined_rect.x0 - 10),
                                max(0, combined_rect.y0 - 10),
                                min(page.rect.width, combined_rect.x1 + 10),
                                min(page.rect.height, combined_rect.y1 + 10)
                            )
                            pix = page.get_pixmap(clip=clip_rect, dpi=150)
                            pix.save(str(img_filepath))
                            pix = None

                            all_visual_elements.append({
                                "element_id": elem_id,
                                "doc_name": pdf_path.name,
                                "page_number": page_num,
                                "element_type": "drawing_render",
                                "image_path": str(img_filepath),
                                "width": w,
                                "height": h
                            })
            except Exception:
                pass  # Graceful fallback for drawing extraction

        doc.close()
        return {
            "doc_name": pdf_path.name,
            "total_pages": total_pages,
            "text_chunks": all_text_chunks,
            "visual_elements": all_visual_elements
        }
