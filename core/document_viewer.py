import re
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple
import pymupdf
from PIL import Image
from core.config import DATA_DIR, EXTRACTED_IMAGES_DIR, EXTRACTED_AUDIO_DIR, EXTRACTED_FRAMES_DIR
from core.media_types import (
    is_image_file,
    is_pdf_file,
    is_audio_file,
    is_video_file,
    get_media_type,
    IMAGE_EXTENSIONS
)

UPLOADS_DIR = DATA_DIR / "uploads"

def resolve_document_path(doc_name: str) -> Optional[Path]:
    """Resolves the physical file path of an uploaded PDF, image, audio, or video."""
    if not doc_name:
        return None

    # 1. Check uploads directory
    candidate = UPLOADS_DIR / doc_name
    if candidate.exists():
        return candidate

    # 2. Check data root directory
    candidate2 = DATA_DIR / doc_name
    if candidate2.exists():
        return candidate2

    # 3. Check extracted images directory
    candidate3 = EXTRACTED_IMAGES_DIR / doc_name
    if candidate3.exists():
        return candidate3

    # 4. Check extracted audio directory
    candidate4 = EXTRACTED_AUDIO_DIR / doc_name
    if candidate4.exists():
        return candidate4

    # 5. Check extracted frames directory
    candidate5 = EXTRACTED_FRAMES_DIR / doc_name
    if candidate5.exists():
        return candidate5

    # 6. Direct path check
    direct = Path(doc_name)
    if direct.exists():
        return direct

    return None

def extract_search_phrases(text: str) -> List[str]:
    """Extracts distinctive phrases from a snippet to maximize hit rate in PDF search."""
    clean = re.sub(r'[\r\n\t]+', ' ', text).strip()
    clean = re.sub(r'\[.*?\]', '', clean).strip()
    # Normalize fancy quotes, hyphens, and whitespace
    clean = re.sub(r'[""«»“”\'`´]', '', clean)
    clean = re.sub(r'[-—–]', ' ', clean)
    clean = re.sub(r'\s+', ' ', clean).strip()

    phrases = []
    # 1. Full cleaned snippet if moderate length
    if len(clean) >= 15 and len(clean) <= 75:
        phrases.append(clean)

    # 2. Distinct sentences
    sentences = [s.strip() for s in re.split(r'[.;!?:]', clean) if len(s.strip()) >= 15]
    for s in sentences[:4]:
        phrases.append(s[:55].strip())

    # 3. Sliding 4-to-5 word windows
    words = clean.split()
    for i in range(0, min(max(0, len(words) - 3), 24), 3):
        chunk = " ".join(words[i:i+5])
        if len(chunk) >= 14:
            phrases.append(chunk)

    return phrases

def render_document_view(
    file_path: Path,
    page_number: int = 1,
    snippet_text: str = "",
    element_id: str = ""
) -> Tuple[bytes, bool, Optional[str]]:
    """
    Renders the document view:
    - If PDF: Renders the requested page at 150 DPI with Riso fluo highlighting (#FF4FA3).
      If an image element is cited on that page, highlights its rect and provides the extracted PNG path.
    - If Image: Returns the raw image bytes.
    Returns (image_bytes, is_highlighted, extracted_image_path).
    """
    file_path = Path(file_path)
    if not file_path.exists():
        raise FileNotFoundError(f"No se encontró el archivo: {file_path}")

    # Case A: Standalone Image
    if is_image_file(file_path.name):
        with open(file_path, "rb") as f:
            return f.read(), True, str(file_path)

    # Case B: PDF Document
    doc = pymupdf.open(str(file_path))
    total_pages = len(doc)
    page_idx = max(0, min(total_pages - 1, page_number - 1))
    page = doc[page_idx]

    highlighted = False
    extracted_img_path = None

    # Check if element_id corresponds to an extracted image from this PDF
    if element_id:
        img_candidate = EXTRACTED_IMAGES_DIR / f"{element_id}.png"
        if img_candidate.exists():
            extracted_img_path = str(img_candidate)

    # 1. Highlight visual image / drawing region on page
    if element_id:
        img_list = page.get_images(full=True)
        if img_list:
            for info in img_list:
                xref = info[0]
                rects = page.get_image_rects(xref)
                if rects:
                    for r in rects:
                        # Draw high-visibility Liquid Creature Poison Orange border and Acid Lime plate
                        page.draw_rect(r, color=(1.0, 0.357, 0.078), width=3.0)  # #FF5B14 Naranja Venenoso
                        page.draw_rect(
                            pymupdf.Rect(r.x0, max(0, r.y0 - 18), min(page.rect.width, r.x0 + 130), r.y0),
                            color=(0.024, 0.102, 0.125),
                            fill=(0.776, 1.0, 0.239)  # #C6FF3D Lima Ácida
                        )
                        page.insert_text((r.x0 + 4, max(12, r.y0 - 5)), "CITA VISUAL", color=(0.024, 0.102, 0.125), fontsize=9)
                        highlighted = True
                        break

        # Check vector drawings if not highlighted yet
        if not highlighted and "drawing" in element_id.lower():
            drawings = page.get_drawings()
            if drawings:
                comb = None
                for d in drawings:
                    r = d["rect"]
                    if r.width > page.rect.width * 0.95 and r.height > page.rect.height * 0.95:
                        continue
                    if comb is None:
                        comb = pymupdf.Rect(r)
                    else:
                        comb |= r
                if comb and comb.is_valid and not comb.is_empty:
                    page.draw_rect(comb, color=(1.0, 0.357, 0.078), width=3.0)
                    page.draw_rect(
                        pymupdf.Rect(comb.x0, max(0, comb.y0 - 18), min(page.rect.width, comb.x0 + 140), comb.y0),
                        color=(0.024, 0.102, 0.125),
                        fill=(0.776, 1.0, 0.239)
                    )
                    page.insert_text((comb.x0 + 4, max(12, comb.y0 - 5)), "GRÁFICO VECTORIAL", color=(0.024, 0.102, 0.125), fontsize=9)
                    highlighted = True

    # 2. Highlight text citation if available
    if snippet_text and not highlighted:
        phrases = extract_search_phrases(snippet_text)
        all_rects = []
        for phrase in phrases:
            rects = page.search_for(phrase)
            if rects:
                all_rects.extend(rects)
                if len(all_rects) >= 4:
                    break

        if all_rects:
            annot = page.add_highlight_annot(all_rects)
            annot.set_colors(stroke=(1.0, 0.357, 0.078))  # #FF5B14 Naranja Venenoso
            annot.update()

            primary_rect = all_rects[0]
            marker_rect = pymupdf.Rect(
                max(0, primary_rect.x0 - 6),
                max(0, primary_rect.y0 - 4),
                min(page.rect.width, primary_rect.x1 + 6),
                min(page.rect.height, primary_rect.y1 + 4)
            )
            page.draw_rect(marker_rect, color=(0.776, 1.0, 0.239), width=1.5, fill=None)  # #C6FF3D Lima Ácida
            highlighted = True

    pix = page.get_pixmap(dpi=150)
    png_bytes = pix.tobytes("png")
    doc.close()

    return png_bytes, highlighted, extracted_img_path

def get_document_page_count(file_path: Path) -> int:
    """Returns page count: 1 for standalone images, len(doc) for PDFs."""
    file_path = Path(file_path)
    if is_image_file(file_path.name):
        return 1
    try:
        doc = pymupdf.open(str(file_path))
        count = len(doc)
        doc.close()
        return count
    except Exception:
        return 1
