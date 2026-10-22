import re
import time
from pathlib import Path
from typing import List, Dict, Any, Generator, Optional, Tuple
import ollama
from PIL import Image

from core.config import VISION_MODEL, VISION_OPTIONS
from core.pdf_extractor import PDFExtractor
from core.stats_manager import StatsManager
from core.vector_store import VectorStore
from core.visual_analyzer import VisualAnalyzer
from core.media_types import get_media_type, format_timestamp, format_time_interval
from core.audio_processor import AudioProcessor
from core.video_processor import VideoProcessor
from core.traceability import trace_manager as default_trace_manager, TraceManager
from core.cloud_llm import stream_cloud_chat, CLOUD_PROVIDERS


def optimize_chat_image(image_path: str, max_dim: int = 512) -> str:
    """Downscales image to max 512px for chat vision to prevent exceeding Ollama context tokens."""
    try:
        p = Path(image_path)
        with Image.open(p) as img:
            if img.width > max_dim or img.height > max_dim:
                img_copy = img.copy()
                img_copy.thumbnail((max_dim, max_dim), Image.Resampling.LANCZOS)
                opt_path = p.parent / f"_chat_opt_{p.name}"
                img_copy.save(opt_path, format="PNG", optimize=True)
                return str(opt_path)
    except Exception:
        pass
    return str(image_path)


VISUAL_QUERY_KEYWORDS = [
    "imagen", "imágenes", "imagenes", "gráfico", "grafico", "gráficos", "graficos",
    "diagrama", "diagramas", "tabla", "tablas", "esquema", "esquemas",
    "figura", "figuras", "foto", "fotos", "fotografía", "fotografia",
    "dibujo", "dibujos", "curva", "curvas", "eje", "ejes", "barra", "barras",
    "página", "pagina", "folio", "folios", "cuántas", "cuantas", "cuántos", "cuantos",
    "video", "fotograma", "cuadro", "escena", "segundo", "minuto", "lapso", "tiempo"
]


def is_visual_query(query: str) -> bool:
    q = query.lower()
    return any(k in q for k in VISUAL_QUERY_KEYWORDS)


def detect_target_documents(user_query: str, available_docs: List[str]) -> List[str]:
    """
    Detects if the user query explicitly mentions or targets one or more of the available documents.
    Normalizes words and scores matches based on document filename, stem, and key tokens.
    """
    if not available_docs:
        return []

    q_lower = user_query.lower()
    accents_map = str.maketrans("áéíóúÁÉÍÓÚñÑ", "aeiouAEIOUnN")
    q_norm = q_lower.translate(accents_map)

    STOP_WORDS = {
        "archivo", "documento", "pliego", "informe", "pdf", "imagen", "foto",
        "audio", "video", "clip", "grabacion", "sobre", "para", "este", "cual",
        "cuales", "como", "donde", "cuando", "que", "los", "las", "del", "por",
        "con", "una", "uno", "unos", "unas"
    }

    doc_scores = {}
    for doc in available_docs:
        doc_stem = Path(doc).stem.lower().translate(accents_map)
        score = 0

        # Exact match of stem or filename
        if doc_stem in q_norm or doc.lower() in q_lower:
            score += 20

        # Split stem into distinctive tokens
        raw_tokens = re.split(r'[-_\s\.,]+', doc_stem)
        tokens = [t for t in raw_tokens if len(t) >= 4 and t not in STOP_WORDS]

        for tok in tokens:
            if tok in q_norm:
                score += 8

        if score > 0:
            doc_scores[doc] = score

    if not doc_scores:
        return []

    sorted_docs = sorted(doc_scores.keys(), key=lambda d: doc_scores[d], reverse=True)
    return sorted_docs


SYSTEM_PROMPT_TEMPLATE = """Eres un Asistente Experto en Análisis Documental y RAG Multimodal Avanzado.
Tienes acceso directo al contenido textual del documento, a análisis profundos de sus elementos visuales (gráficos, diagramas, tablas y fotos), a transcripciones completas de pistas de audio, y a fotogramas de video con comprensión visual en tiempo real.

{stats_sheet}

INSTRUCCIONES CRÍTICAS:
1. EXACTITUD EN CONTEOS Y METADATOS:
   - Para responder preguntas sobre el número total de páginas, duración, conteo de imágenes, gráficos estadísticos, diagramas, tablas o segmentos sonoros, básate EXCLUSIVAMENTE en la Ficha Técnica Global proporcionada arriba.
   - NUNCA intentes deducir totales o duración a partir únicamente de los fragmentos recuperados.
2. FIDELIDAD AL CONTEXTO Y CITACIONES DE TIEMPO / PÁGINA:
   - Fundamenta tus explicaciones en los fragmentos recuperados.
   - Para pliegos PDF cita siempre la página relevante (ej. "[Página 4]").
   - Para archivos de AUDIO y VIDEO cita SIEMPRE el lapso de tiempo exacto donde ocurre la evidencia (ej. "[⏱️ 01:23 - 01:45]" o "[⏱️ 00:30]").
   - En videos, distingue con claridad cuando la información proviene de lo que se visualiza en la pantalla (fotograma/gráfico/texto visible) o de lo que se escucha (locución/pista de audio).
3. ANÁLISIS VISUAL EN TIEMPO REAL:
   - Cuando se hayan adjuntado imágenes originales o fotogramas a esta conversación, examina sus píxeles, curvas, ejes numéricos, barras, títulos y anotaciones directamente.
   - Explica detalladamente lo que visualizas y cómo se correlaciona con el texto y el audio.
4. Si la información solicitada no se encuentra en el documento, indícalo con honestidad sin inventar.
5. Responde siempre en español de forma profesional, clara, estructurada y pedagógica.
"""


class RAGEngine:
    def __init__(
        self,
        vector_store: Optional[VectorStore] = None,
        stats_manager: Optional[StatsManager] = None,
        visual_analyzer: Optional[VisualAnalyzer] = None,
        pdf_extractor: Optional[PDFExtractor] = None,
        audio_processor: Optional[AudioProcessor] = None,
        video_processor: Optional[VideoProcessor] = None,
        trace_manager: Optional[TraceManager] = None,
    ):
        self.vector_store = vector_store or VectorStore()
        self.stats_manager = stats_manager or StatsManager()
        self.visual_analyzer = visual_analyzer or VisualAnalyzer()
        self.pdf_extractor = pdf_extractor or PDFExtractor()
        self.audio_processor = audio_processor or AudioProcessor()
        self.video_processor = video_processor or VideoProcessor(
            audio_processor=self.audio_processor,
            visual_analyzer=self.visual_analyzer
        )
        self.trace_manager = trace_manager or default_trace_manager
        self.ollama_client = ollama.Client()

    def index_document(
        self,
        file_path: Path,
        progress_callback: Optional[callable] = None
    ) -> Dict[str, Any]:
        """
        Executes complete ingestion pipeline:
        - If Audio: Normalization to WAV, slicing, speech-to-text with timestamps, Qdrant & SQLite storage.
        - If Video: Audio track transcription + keyframe extraction & visual comprehension with Qwen2.5-VL.
        - If Standalone Image: Single-specimen comprehension with Qwen2.5-VL.
        - If PDF: PyMuPDF extraction (text + visual elements + vector drawings).
        """
        file_path = Path(file_path)
        doc_name = file_path.name
        m_type = get_media_type(file_path)
        flow_type = f"ingestion_{m_type}"

        trace_id = self.trace_manager.start_trace(
            flow_type=flow_type,
            title=f"Ingestión de {m_type.upper()}: {doc_name}",
            metadata={"doc_name": doc_name, "media_type": m_type, "file_path": str(file_path)}
        )

        try:
            # Clean existing records for this document
            t0 = time.perf_counter()
            self.vector_store.delete_document_points(doc_name)
            self.trace_manager.add_step(
                trace_id,
                step_name="Purga de Vectores Previos",
                details=f"Limpieza de puntos vectoriales existentes en Qdrant para '{doc_name}'",
                duration_ms=(time.perf_counter() - t0) * 1000
            )

            # ── 1. AUDIO SPECIMEN ──────────────────────────────────────────
            if m_type == "audio":
                if progress_callback:
                    progress_callback(0.1, f"Analizando registro sonoro '{doc_name}'...")

                t_proc = time.perf_counter()
                audio_res = self.audio_processor.process_audio(
                    file_path,
                    doc_name=doc_name,
                    progress_callback=progress_callback
                )
                self.trace_manager.add_step(
                    trace_id,
                    step_name="Normalización de Audio y Transcripción ASR",
                    details=f"Duración: {audio_res['duration_str']} · {len(audio_res['chunks'])} segmentos con intervalos de tiempo generados",
                    duration_ms=(time.perf_counter() - t_proc) * 1000,
                    metadata={"duration": audio_res["duration"], "chunks_count": len(audio_res["chunks"])}
                )

                t_reg = time.perf_counter()
                self.stats_manager.register_document(
                    doc_name=doc_name,
                    file_path=str(file_path),
                    total_pages=1,
                    media_type="audio",
                    duration=audio_res["duration"],
                    duration_str=audio_res["duration_str"]
                )

                for seg in audio_res["chunks"]:
                    self.stats_manager.add_media_segment(
                        doc_name=doc_name,
                        chunk_id=seg["chunk_id"],
                        start_time=seg["start_time"],
                        end_time=seg["end_time"],
                        timestamp_label=seg["timestamp_label"],
                        content=seg["content"],
                        raw_text=seg.get("raw_text", ""),
                        source_type="audio_transcript"
                    )

                self.trace_manager.add_step(
                    trace_id,
                    step_name="Registro en Base de Datos SQLite",
                    details=f"Metadatos y {len(audio_res['chunks'])} segmentos registrados en tabla media_segments",
                    duration_ms=(time.perf_counter() - t_reg) * 1000
                )

                if progress_callback:
                    progress_callback(0.85, "Vectorizando transcripciones de audio en Qdrant...")

                t_vec = time.perf_counter()
                self.vector_store.upsert_text_chunks(audio_res["chunks"])
                self.stats_manager.update_document_summary(doc_name, len(audio_res["chunks"]))
                self.trace_manager.add_step(
                    trace_id,
                    step_name="Vectorización en Qdrant (EmbeddingGemma-2)",
                    details=f"{len(audio_res['chunks'])} vectores indexados en CPU aislada (puerto 6333)",
                    duration_ms=(time.perf_counter() - t_vec) * 1000
                )

                if progress_callback:
                    progress_callback(1.0, "¡Registro sonoro catalogado e indexado con éxito!")

                self.trace_manager.complete_trace(
                    trace_id,
                    status="success",
                    summary=f"Audio '{doc_name}' ({audio_res['duration_str']}) indexado con {len(audio_res['chunks'])} segmentos temporizados."
                )

                return self.stats_manager.get_document_stats(doc_name)

            # ── 2. VIDEO SPECIMEN ──────────────────────────────────────────
            if m_type == "video":
                if progress_callback:
                    progress_callback(0.05, f"Iniciando procesamiento audiovisual de '{doc_name}'...")

                t_proc = time.perf_counter()
                video_res = self.video_processor.process_video(
                    file_path,
                    progress_callback=progress_callback
                )

                audio_chunks = video_res.get("audio_chunks", [])
                visual_frames = video_res.get("visual_elements", [])
                self.trace_manager.add_step(
                    trace_id,
                    step_name="Descomposición Audiovisual Dual (ASR + Visión VL)",
                    details=f"Duración: {video_res['duration_str']} · {len(audio_chunks)} segmentos de audio + {len(visual_frames)} fotogramas clave analizados con Qwen2.5-VL",
                    duration_ms=(time.perf_counter() - t_proc) * 1000,
                    metadata={"audio_chunks": len(audio_chunks), "visual_frames": len(visual_frames), "duration": video_res["duration"]}
                )

                t_reg = time.perf_counter()
                self.stats_manager.register_document(
                    doc_name=doc_name,
                    file_path=str(file_path),
                    total_pages=max(1, len(visual_frames)),
                    media_type="video",
                    duration=video_res["duration"],
                    duration_str=video_res["duration_str"]
                )

                for seg in audio_chunks:
                    self.stats_manager.add_media_segment(
                        doc_name=doc_name,
                        chunk_id=seg["chunk_id"],
                        start_time=seg["start_time"],
                        end_time=seg["end_time"],
                        timestamp_label=seg["timestamp_label"],
                        content=seg["content"],
                        raw_text=seg.get("raw_text", ""),
                        source_type="video_audio_transcript"
                    )

                if audio_chunks:
                    self.vector_store.upsert_text_chunks(audio_chunks)

                frame_chunks_for_text_search = []
                for frame in visual_frames:
                    self.stats_manager.add_visual_element(
                        doc_name=doc_name,
                        element_id=frame["element_id"],
                        page_number=frame["page_number"],
                        element_type="video_frame",
                        image_path=frame["image_path"],
                        width=frame["width"],
                        height=frame["height"],
                        start_time=frame["start_time"],
                        end_time=frame["end_time"],
                        timestamp_label=frame["timestamp_label"]
                    )
                    self.stats_manager.update_visual_element_analysis(
                        element_id=frame["element_id"],
                        visual_category=frame["visual_category"],
                        description=frame["description"],
                        transcribed_text=frame.get("transcription", "")
                    )
                    self.vector_store.upsert_visual_element(
                        doc_name=doc_name,
                        element_id=frame["element_id"],
                        page_number=frame["page_number"],
                        visual_category=frame["visual_category"],
                        description=frame["description"],
                        transcription=frame.get("transcription", ""),
                        image_path=frame["image_path"],
                        start_time=frame["start_time"],
                        end_time=frame["end_time"],
                        timestamp_label=frame["timestamp_label"],
                        media_type="video"
                    )

                    frame_desc = (
                        f"[FOTOGRAMA VIDEO {doc_name} | {frame['timestamp_label']}] "
                        f"[{frame['visual_category']}].\n"
                        f"Texto visible: {frame.get('transcription', '')}\n"
                        f"Descripción de la escena: {frame['description']}"
                    )
                    frame_chunks_for_text_search.append({
                        "chunk_id": f"{frame['element_id']}_txt",
                        "doc_name": doc_name,
                        "page_number": frame["page_number"],
                        "start_time": frame["start_time"],
                        "end_time": frame["end_time"],
                        "timestamp_label": frame["timestamp_label"],
                        "content": frame_desc,
                        "source_type": "visual",
                        "media_type": "video",
                        "image_path": frame["image_path"],
                        "visual_category": frame["visual_category"]
                    })

                if frame_chunks_for_text_search:
                    self.vector_store.upsert_text_chunks(frame_chunks_for_text_search)

                self.stats_manager.update_document_summary(
                    doc_name, len(audio_chunks) + len(frame_chunks_for_text_search)
                )

                self.trace_manager.add_step(
                    trace_id,
                    step_name="Registro en SQLite y Vectorización en Qdrant",
                    details=f"Persistidos {len(visual_frames)} fotogramas y {len(audio_chunks)} fragmentos de audio en SQLite + Colección Qdrant",
                    duration_ms=(time.perf_counter() - t_reg) * 1000
                )

                if progress_callback:
                    progress_callback(1.0, "¡Archivo audiovisual analizado e indexado con éxito!")

                self.trace_manager.complete_trace(
                    trace_id,
                    status="success",
                    summary=f"Video '{doc_name}' ({video_res['duration_str']}) indexado: {len(visual_frames)} fotogramas en GPU y {len(audio_chunks)} transcripciones sonoras."
                )

                return self.stats_manager.get_document_stats(doc_name)

            # ── 3. STANDALONE IMAGE ────────────────────────────────────────
            if m_type == "image":
                if progress_callback:
                    progress_callback(0.2, f"Catalogando espécimen visual '{doc_name}'...")

                with Image.open(file_path) as img:
                    w, h = img.size

                self.stats_manager.register_document(doc_name, str(file_path), total_pages=1, media_type="image")

                if progress_callback:
                    progress_callback(0.4, "Comprendiendo imagen con Qwen2.5-VL (GPU)...")

                t_vl = time.perf_counter()
                analysis = self.visual_analyzer.analyze_image(file_path)
                category = analysis.get("categoria", "Fotografía/Ilustración")
                transcription = analysis.get("transcripcion", "")
                description = analysis.get("descripcion_detallada", "")
                self.trace_manager.add_step(
                    trace_id,
                    step_name="Comprensión Visual en Qwen2.5-VL (GPU)",
                    details=f"Categoría: {category} · Texto OCR: {len(transcription)} car. · Descripción: {len(description)} car.",
                    duration_ms=(time.perf_counter() - t_vl) * 1000
                )

                elem_id = f"{file_path.stem}_img1"

                self.stats_manager.add_visual_element(
                    doc_name=doc_name,
                    element_id=elem_id,
                    page_number=1,
                    element_type="standalone_image",
                    image_path=str(file_path),
                    width=w,
                    height=h
                )
                self.stats_manager.update_visual_element_analysis(
                    element_id=elem_id,
                    visual_category=category,
                    description=description,
                    transcribed_text=transcription
                )

                if progress_callback:
                    progress_callback(0.7, "Generando vector semántico (EmbeddingGemma-2 en CPU)...")

                t_vec = time.perf_counter()
                self.vector_store.upsert_visual_element(
                    doc_name=doc_name,
                    element_id=elem_id,
                    page_number=1,
                    visual_category=category,
                    description=description,
                    transcription=transcription,
                    image_path=str(file_path),
                    media_type="image"
                )

                rich_chunk_content = f"Espécimen de imagen: {doc_name}.\nCategoría: {category}.\n"
                if transcription:
                    rich_chunk_content += f"Texto visible y datos: {transcription}\n"
                rich_chunk_content += f"Descripción visual: {description}"

                self.vector_store.upsert_text_chunks([{
                    "chunk_id": f"{file_path.stem}_chunk1",
                    "doc_name": doc_name,
                    "page_number": 1,
                    "content": rich_chunk_content,
                    "source_type": "visual",
                    "media_type": "image"
                }])

                self.stats_manager.update_document_summary(doc_name, total_text_chunks=1)
                self.trace_manager.add_step(
                    trace_id,
                    step_name="Vectorización en Qdrant (EmbeddingGemma-2)",
                    details="Vector semántico indexado en CPU aislada (dimensión 768)",
                    duration_ms=(time.perf_counter() - t_vec) * 1000
                )

                if progress_callback:
                    progress_callback(1.0, "¡Espécimen visual catalogado e indexado con éxito!")

                self.trace_manager.complete_trace(
                    trace_id,
                    status="success",
                    summary=f"Imagen '{doc_name}' catalogada y vectorizada ({category})."
                )

                return self.stats_manager.get_document_stats(doc_name)

            # ── 4. PDF DOCUMENT ───────────────────────────────────────────
            if progress_callback:
                progress_callback(0.1, "Extrayendo texto y elementos visuales del PDF...")

            t_pdf = time.perf_counter()
            extracted = self.pdf_extractor.process_pdf(
                pdf_path=file_path,
                progress_callback=lambda curr, total, txt: progress_callback(
                    0.1 + 0.3 * (curr / total), txt
                ) if progress_callback else None
            )

            total_pages = extracted["total_pages"]
            text_chunks = extracted["text_chunks"]
            visual_elements = extracted["visual_elements"]
            self.trace_manager.add_step(
                trace_id,
                step_name="Extracción PyMuPDF (Texto y Gráficos)",
                details=f"{total_pages} páginas procesadas · {len(text_chunks)} fragmentos de texto · {len(visual_elements)} elementos visuales extraídos",
                duration_ms=(time.perf_counter() - t_pdf) * 1000
            )

            # Register document
            self.stats_manager.register_document(doc_name, str(file_path), total_pages, media_type="pdf")

            # Process Visual Elements with Qwen2.5-VL
            t_vl = time.perf_counter()
            total_visual = len(visual_elements)
            for idx, elem in enumerate(visual_elements):
                if progress_callback:
                    progress_callback(
                        0.4 + 0.35 * ((idx + 1) / max(1, total_visual)),
                        f"Comprendiendo imagen/gráfico {idx + 1} de {total_visual} (Pág. {elem['page_number']}) con Qwen2.5-VL..."
                    )

                self.stats_manager.add_visual_element(
                    doc_name=doc_name,
                    element_id=elem["element_id"],
                    page_number=elem["page_number"],
                    element_type=elem["element_type"],
                    image_path=elem["image_path"],
                    width=elem["width"],
                    height=elem["height"]
                )

                analysis = self.visual_analyzer.analyze_image(Path(elem["image_path"]))
                category = analysis["categoria"]
                transcription = analysis["transcripcion"]
                description = analysis["descripcion_detallada"]

                self.stats_manager.update_visual_element_analysis(
                    element_id=elem["element_id"],
                    visual_category=category,
                    description=description,
                    transcribed_text=transcription
                )

                self.vector_store.upsert_visual_element(
                    doc_name=doc_name,
                    element_id=elem["element_id"],
                    page_number=elem["page_number"],
                    visual_category=category,
                    description=description,
                    transcription=transcription,
                    image_path=elem["image_path"],
                    media_type="pdf"
                )

            if total_visual > 0:
                self.trace_manager.add_step(
                    trace_id,
                    step_name="Comprensión Visual en GPU (Qwen2.5-VL)",
                    details=f"{total_visual} figuras/gráficos analizados y descritos detalladamente",
                    duration_ms=(time.perf_counter() - t_vl) * 1000
                )

            if progress_callback:
                progress_callback(0.8, "Vectorizando fragmentos de texto en Qdrant (EmbeddingGemma-2 en CPU)...")

            t_vec = time.perf_counter()
            for c in text_chunks:
                c["media_type"] = "pdf"
            self.vector_store.upsert_text_chunks(text_chunks)
            self.stats_manager.update_document_summary(doc_name, len(text_chunks))
            self.trace_manager.add_step(
                trace_id,
                step_name="Vectorización en Qdrant (EmbeddingGemma-2)",
                details=f"{len(text_chunks)} fragmentos de texto vectorizados en CPU aislada e indexados",
                duration_ms=(time.perf_counter() - t_vec) * 1000
            )

            if progress_callback:
                progress_callback(1.0, "¡Indexación multimodal completada con éxito!")

            self.trace_manager.complete_trace(
                trace_id,
                status="success",
                summary=f"Pliego PDF '{doc_name}' ({total_pages} pág.) indexado con {len(text_chunks)} fragmentos y {total_visual} elementos visuales."
            )

            return self.stats_manager.get_document_stats(doc_name)

        except Exception as e:
            self.trace_manager.add_step(
                trace_id,
                step_name="Fallo en la Ingestión",
                details=str(e),
                status="error"
            )
            self.trace_manager.complete_trace(
                trace_id,
                status="error",
                summary=f"Error durante la ingestión: {str(e)}"
            )
            raise

    def delete_document(self, doc_name: str, uploads_dir: Optional[Path] = None) -> bool:
        """
        Permanently deletes a document and all related data:
        1. Vectors in Qdrant.
        2. Records in SQLite (documents, visual_elements, media_segments).
        3. Physical files in uploads and extracted artifacts directories.
        """
        from core.config import DATA_DIR, EXTRACTED_IMAGES_DIR, EXTRACTED_AUDIO_DIR, EXTRACTED_FRAMES_DIR
        from core.media_types import sanitize_filename

        trace_id = self.trace_manager.start_trace(
            flow_type="deletion",
            title=f"Eliminación y Purga: {doc_name}",
            metadata={"doc_name": doc_name}
        )

        # 1. Remove vectors from Qdrant
        t0 = time.perf_counter()
        try:
            self.vector_store.delete_document_points(doc_name)
            dur = (time.perf_counter() - t0) * 1000
            self.trace_manager.add_step(
                trace_id, "Purga de Vectores en Qdrant",
                details=f"Puntos vectoriales borrados para '{doc_name}'",
                duration_ms=dur
            )
        except Exception as e:
            self.trace_manager.add_step(trace_id, "Purga en Qdrant", details=str(e), status="warning")

        # 2. Remove records from SQLite
        t0 = time.perf_counter()
        try:
            self.stats_manager.delete_document(doc_name)
            dur = (time.perf_counter() - t0) * 1000
            self.trace_manager.add_step(
                trace_id, "Eliminación en SQLite",
                details="Registros de documento, elementos visuales y segmentos sonoros eliminados",
                duration_ms=dur
            )
        except Exception as e:
            self.trace_manager.add_step(trace_id, "Eliminación en SQLite", details=str(e), status="warning")

        # 3. Remove physical uploaded file
        t0 = time.perf_counter()
        u_dir = uploads_dir or (DATA_DIR / "uploads")
        try:
            target_file = u_dir / doc_name
            removed_file = False
            if target_file.exists():
                target_file.unlink()
                removed_file = True
            dur = (time.perf_counter() - t0) * 1000
            self.trace_manager.add_step(
                trace_id, "Eliminación de Archivo en Disco",
                details=f"Archivo '{target_file.name}' {'eliminado de disco' if removed_file else 'no encontrado'}",
                duration_ms=dur
            )
        except Exception as e:
            self.trace_manager.add_step(trace_id, "Eliminación en Disco", details=str(e), status="warning")

        # 4. Remove extracted visual/audio artifacts
        t0 = time.perf_counter()
        safe_stem = sanitize_filename(Path(doc_name).stem)
        cleaned_artifacts = 0
        for folder in [EXTRACTED_IMAGES_DIR, EXTRACTED_AUDIO_DIR, EXTRACTED_FRAMES_DIR]:
            if folder.exists():
                try:
                    for artifact in folder.glob(f"*{safe_stem}*"):
                        try:
                            artifact.unlink()
                            cleaned_artifacts += 1
                        except Exception:
                            pass
                except Exception:
                    pass

        dur = (time.perf_counter() - t0) * 1000
        self.trace_manager.add_step(
            trace_id, "Limpieza de Artefactos de Caché",
            details=f"{cleaned_artifacts} archivos auxiliares eliminados (fotogramas, audios WAV, recortes)",
            duration_ms=dur
        )

        self.trace_manager.complete_trace(
            trace_id,
            status="success",
            summary=f"Documento '{doc_name}' y todos sus vectores y artefactos purgados por completo."
        )

        return True

    def delete_all_documents(self, uploads_dir: Optional[Path] = None) -> bool:
        """Permanently wipes all documents, vectors, records, and extracted files."""
        from core.config import DATA_DIR, EXTRACTED_IMAGES_DIR, EXTRACTED_AUDIO_DIR, EXTRACTED_FRAMES_DIR

        try:
            self.vector_store.delete_all_points()
        except Exception as e:
            print(f"[RAGEngine] Notice wiping Qdrant: {e}")

        try:
            self.stats_manager.delete_all_documents()
        except Exception as e:
            print(f"[RAGEngine] Notice wiping SQLite: {e}")

        u_dir = uploads_dir or (DATA_DIR / "uploads")
        for folder in [u_dir, EXTRACTED_IMAGES_DIR, EXTRACTED_AUDIO_DIR, EXTRACTED_FRAMES_DIR]:
            if folder.exists():
                try:
                    for f in folder.iterdir():
                        if f.is_file():
                            try:
                                f.unlink()
                            except Exception:
                                pass
                except Exception:
                    pass

        return True

    def extract_page_mentions(self, text: str) -> List[int]:
        """Finds any page numbers mentioned in user prompt (e.g. 'página 3', 'pág 5', 'p. 2')."""
        matches = re.findall(r'(?:p[aá]gina|p[aá]g\.?|p\.)\s*(\d+)', text, re.IGNORECASE)
        return [int(m) for m in matches]

    def query(
        self,
        doc_names: Optional[Any] = None,
        user_query: str = "",
        chat_history: Optional[List[Dict[str, str]]] = None,
        top_k: int = 5,
        doc_name: Optional[str] = None,
        llm_mode: str = "local",
        cloud_config: Optional[Dict[str, Any]] = None,
    ) -> Tuple[Generator[str, None, None], List[Dict[str, Any]]]:
        """
        Executes Hybrid Multimodal Retrieval across one or multiple documents associated with a chat:
        - Injects global statistical sheet for all target documents.
        - Retrieves top-k relevant fragments prioritized from the target documents.
        - Passes PNG paths in `images` parameter to Qwen2.5-VL for visual comprehension.
        - Streams response back with exact timestamp citations for audio/video.
        """
        target_docs = []
        if isinstance(doc_names, str):
            target_docs.append(doc_names)
        elif isinstance(doc_names, (list, tuple, set)):
            target_docs.extend([d for d in doc_names if d])
        elif doc_name:
            target_docs.append(doc_name)

        q_snippet = user_query[:32] + ("…" if len(user_query) > 32 else "")
        trace_id = self.trace_manager.start_trace(
            flow_type="query",
            title=f"Consulta: '{q_snippet}'",
            metadata={"user_query": user_query, "target_docs": target_docs, "top_k": top_k}
        )

        # 1. Retrieve relevant fragments from Qdrant, prioritizing explicitly mentioned documents
        detected_docs = detect_target_documents(user_query, target_docs)
        self.trace_manager.add_step(
            trace_id,
            step_name="Identificación de Pliegos Objetivo",
            details=f"Pliegos detectados prioritarios: {detected_docs}" if detected_docs else f"Búsqueda balanceada en todos los pliegos vinculados: {target_docs}",
            metadata={"detected_docs": detected_docs}
        )

        t_search = time.perf_counter()
        if detected_docs:
            primary_hits = self.vector_store.search(
                query=user_query,
                doc_names=detected_docs,
                limit=top_k
            )
            if len(primary_hits) < top_k:
                other_docs = [d for d in target_docs if d not in detected_docs]
                if other_docs:
                    secondary_hits = self.vector_store.search(
                        query=user_query,
                        doc_names=other_docs,
                        limit=top_k - len(primary_hits)
                    )
                    retrieved_hits = primary_hits + secondary_hits
                else:
                    retrieved_hits = primary_hits
            else:
                retrieved_hits = primary_hits
        else:
            retrieved_hits = self.vector_store.search(
                query=user_query,
                doc_names=target_docs if target_docs else None,
                limit=top_k
            )

        dur_search = (time.perf_counter() - t_search) * 1000
        self.trace_manager.add_step(
            trace_id,
            step_name="Recuperación Vectorial en Qdrant (EmbeddingGemma-2)",
            details=f"{len(retrieved_hits)} fragmentos coincidentes recuperados con similitud de coseno en CPU",
            duration_ms=dur_search,
            metadata={"hits_count": len(retrieved_hits)}
        )

        # 2. Check for specific page mentions across all target documents
        mentioned_pages = self.extract_page_mentions(user_query)
        all_doc_elements = []
        for d in target_docs:
            d_stats = self.stats_manager.get_document_stats(d) or {}
            all_doc_elements.extend(d_stats.get("elements", []))

        # 3. Collect images / frames for real-time visual inspection
        inspected_images = []
        inspected_paths_set = set()

        for hit in retrieved_hits:
            if (hit.get("source_type") == "visual" or hit.get("media_type") == "video") and hit.get("image_path"):
                path = hit["image_path"]
                if Path(path).exists() and path not in inspected_paths_set:
                    inspected_paths_set.add(path)
                    inspected_images.append({
                        "id": hit["element_id"],
                        "page": hit.get("page_number", 1),
                        "start_time": hit.get("start_time", 0.0),
                        "end_time": hit.get("end_time", 0.0),
                        "timestamp_label": hit.get("timestamp_label", ""),
                        "category": hit.get("visual_category", "Visual"),
                        "path": path,
                        "description": hit["content"],
                        "doc_name": hit.get("doc_name", ""),
                        "media_type": hit.get("media_type", "image")
                    })

        for page in mentioned_pages:
            for elem in all_doc_elements:
                if elem.get("page_number") == page:
                    path = elem["image_path"]
                    if Path(path).exists() and path not in inspected_paths_set:
                        inspected_paths_set.add(path)
                        inspected_images.append({
                            "id": elem["element_id"],
                            "page": elem["page_number"],
                            "start_time": elem.get("start_time", 0.0),
                            "end_time": elem.get("end_time", 0.0),
                            "timestamp_label": elem.get("timestamp_label", ""),
                            "category": elem.get("visual_category", "Visual"),
                            "path": path,
                            "description": elem.get("description", ""),
                            "doc_name": elem.get("doc_name", ""),
                            "media_type": elem.get("media_type", "image")
                        })

        # Attach image ONLY if the user query is explicitly visual or targets specific pages/frames
        if (is_visual_query(user_query) or mentioned_pages) and inspected_images:
            inspected_images = inspected_images[:1]
            image_paths_for_model = [optimize_chat_image(img["path"], max_dim=512) for img in inspected_images]
        else:
            inspected_images = []
            image_paths_for_model = []

        # 4. Extract citations / evidence sources for interactive viewer
        citations = []
        for hit in retrieved_hits[:4]:
            if hit.get("doc_name"):
                citations.append({
                    "doc_name": hit.get("doc_name", ""),
                    "page_number": hit.get("page_number", 1),
                    "start_time": hit.get("start_time", 0.0),
                    "end_time": hit.get("end_time", 0.0),
                    "timestamp_label": hit.get("timestamp_label", ""),
                    "media_type": hit.get("media_type", "pdf"),
                    "source_type": hit.get("source_type", "text"),
                    "visual_category": hit.get("visual_category", "None"),
                    "snippet": hit.get("content", "")[:180],
                    "element_id": hit.get("element_id", "")
                })

        # Ensure directly inspected visual elements are present as citations
        for img in inspected_images:
            if not any(c.get("element_id") == img["id"] for c in citations):
                citations.insert(0, {
                    "doc_name": img.get("doc_name") or (target_docs[0] if target_docs else ""),
                    "page_number": img.get("page", 1),
                    "start_time": img.get("start_time", 0.0),
                    "end_time": img.get("end_time", 0.0),
                    "timestamp_label": img.get("timestamp_label", ""),
                    "media_type": img.get("media_type", "image"),
                    "source_type": "visual",
                    "visual_category": img.get("category", "Espécimen Visual"),
                    "snippet": img.get("description", "")[:180],
                    "element_id": img["id"]
                })

        self.trace_manager.add_step(
            trace_id,
            step_name="Re-inspección Visual y Extracción de Citas",
            details=f"{len(inspected_images)} especímenes visuales/fotogramas inspeccionados · {len(citations)} citas extraídas con intervalos temporales y folios",
            metadata={"inspected_count": len(inspected_images), "citations_count": len(citations)}
        )

        # 5. Build Compact Context String with timestamp clarity
        context_parts = []
        for i, hit in enumerate(retrieved_hits[:3]):
            origin = f" [{hit['doc_name']}]" if hit.get("doc_name") else ""
            content_snippet = hit["content"][:400]
            t_lbl = hit.get("timestamp_label", "")
            time_tag = f" (⏱️ {t_lbl})" if t_lbl else f" (Pág. {hit.get('page_number', 1)})"

            m_type = hit.get("media_type", "")
            s_type = hit.get("source_type", "")

            if m_type == "audio" or "audio" in s_type:
                context_parts.append(
                    f"--- SEGMENTO DE AUDIO {i+1}{origin}{time_tag} ---\n{content_snippet}"
                )
            elif m_type == "video" and s_type == "visual":
                context_parts.append(
                    f"--- FOTOGRAMA DE VIDEO {i+1}{origin} [{hit.get('visual_category', 'Escena')}]{time_tag} ---\n{content_snippet}"
                )
            elif s_type == "visual":
                context_parts.append(
                    f"--- ELEMENTO VISUAL {i+1}{origin} [{hit.get('visual_category', 'Espécimen')}]{time_tag} ---\n{content_snippet}"
                )
            else:
                context_parts.append(
                    f"--- FRAGMENTO {i+1}{origin}{time_tag} ---\n{content_snippet}"
                )

        context_str = "\n\n".join(context_parts) if context_parts else "(No se encontraron fragmentos coincidentes)"
        context_str = context_str[:1400]

        # 6. Build System Prompt with Global Statistical Sheet
        stats_sheet = self.stats_manager.format_stats_sheet(target_docs)
        system_content = SYSTEM_PROMPT_TEMPLATE.format(stats_sheet=stats_sheet)

        self.trace_manager.add_step(
            trace_id,
            step_name="Síntesis de Prompt y Ficha Técnica Global",
            details=f"Ficha técnica ({len(stats_sheet)} car.) + contexto documental ({len(context_str)} car.) inyectados",
            metadata={"context_chars": len(context_str), "stats_sheet_chars": len(stats_sheet)}
        )

        messages = [
            {"role": "system", "content": system_content}
        ]

        if chat_history:
            for turn in chat_history[-2:]:
                turn_content = turn.get("content", "")[:250]
                messages.append({"role": turn["role"], "content": turn_content})

        current_content = (
            f"CONTEXTO RECUPERADO DEL DOCUMENTO:\n{context_str}\n\n"
            f"PREGUNTA DEL USUARIO:\n{user_query}"
        )

        user_message = {
            "role": "user",
            "content": current_content
        }

        if image_paths_for_model:
            user_message["images"] = image_paths_for_model

        messages.append(user_message)

        # 7. Call LLM (Cloud API or Local Ollama Qwen2.5-VL)
        if llm_mode == "cloud":
            cloud_cfg = cloud_config or {}
            provider = cloud_cfg.get("provider", "groq")
            api_key = (cloud_cfg.get("api_key") or "").strip()
            model = cloud_cfg.get("model") or CLOUD_PROVIDERS.get(provider, {}).get("default_model", "llama-3.3-70b-versatile")
            custom_url = cloud_cfg.get("custom_url")

            if not api_key:
                def missing_key_gen() -> Generator[str, None, None]:
                    yield (
                        "⚠️ **Modo Nube activado**: No se ha detectado una clave de API.\n\n"
                        "Por favor, ingresa tu **API Key** en el panel lateral izquierdo "
                        "(sección *🤖 MOTOR DE CHAT* → *Nube*) para poder procesar la consulta de manera segura."
                    )
                    self.trace_manager.add_step(
                        trace_id,
                        step_name="Aviso de Seguridad: Falta API Key",
                        details="El usuario activó el modelo en la nube pero no ha ingresado una clave API en la sesión",
                        status="warning"
                    )
                    self.trace_manager.complete_trace(
                        trace_id,
                        status="warning",
                        summary="Consulta detenida: falta ingresar API Key de la nube."
                    )
                return missing_key_gen(), citations

            def cloud_stream_generator() -> Generator[str, None, None]:
                stream_start = time.perf_counter()
                token_count = 0
                first_token_time = None
                try:
                    cloud_stream = stream_cloud_chat(
                        messages=messages,
                        provider=provider,
                        api_key=api_key,
                        model=model,
                        custom_url=custom_url,
                    )
                    for chunk in cloud_stream:
                        if first_token_time is None:
                            first_token_time = time.perf_counter()
                        token_count += 1
                        yield chunk

                    total_dur = (time.perf_counter() - stream_start) * 1000
                    ttft_ms = ((first_token_time - stream_start) * 1000) if first_token_time else 0
                    self.trace_manager.add_step(
                        trace_id,
                        step_name=f"Inferencia en la Nube ({provider.upper()} · {model})",
                        details=f"Generación en la nube completada en {total_dur/1000:.2f}s · Tiempo al 1er token: {ttft_ms:.0f}ms · ~{token_count} fragmentos emitidos",
                        duration_ms=total_dur,
                        metadata={"provider": provider, "model": model, "total_ms": total_dur, "ttft_ms": ttft_ms, "tokens": token_count}
                    )
                    self.trace_manager.complete_trace(
                        trace_id,
                        status="success",
                        summary=f"Consulta RAG resuelta vía API de {provider} ({model}) en {total_dur/1000:.2f}s ({len(citations)} citas generadas)."
                    )
                except Exception as e:
                    self.trace_manager.add_step(
                        trace_id,
                        step_name="Error en Inferencia Cloud LLM",
                        details=str(e),
                        status="error"
                    )
                    self.trace_manager.complete_trace(
                        trace_id,
                        status="error",
                        summary=f"Error en API Cloud: {str(e)}"
                    )
                    yield f"\n\n*(Error al consultar API en la nube: {str(e)})*"

            return cloud_stream_generator(), citations

        # 7b. Call Local Qwen2.5-VL with streaming and safe fallback
        try:
            response_stream = self.ollama_client.chat(
                model=VISION_MODEL,
                messages=messages,
                options=VISION_OPTIONS,
                stream=True
            )
        except Exception:
            fallback_user_msg = {
                "role": "user",
                "content": f"Contexto breve:\n{context_str[:800]}\n\nPregunta: {user_query}"
            }
            response_stream = self.ollama_client.chat(
                model=VISION_MODEL,
                messages=[{"role": "system", "content": "Responde de forma clara y precisa en español basándote en los documentos."}, fallback_user_msg],
                options=VISION_OPTIONS,
                stream=True
            )

        def stream_generator() -> Generator[str, None, None]:
            stream_start = time.perf_counter()
            token_count = 0
            first_token_time = None
            try:
                for chunk in response_stream:
                    content = chunk.message.content
                    if content:
                        if first_token_time is None:
                            first_token_time = time.perf_counter()
                        token_count += 1
                        yield content

                total_stream_dur = (time.perf_counter() - stream_start) * 1000
                ttft_ms = ((first_token_time - stream_start) * 1000) if first_token_time else 0
                self.trace_manager.add_step(
                    trace_id,
                    step_name="Inferencia Multimodal en Qwen2.5-VL (GPU)",
                    details=f"Generación completada en {total_stream_dur/1000:.2f}s · Tiempo al 1er token: {ttft_ms:.0f}ms · ~{token_count} fragmentos emitidos",
                    duration_ms=total_stream_dur,
                    metadata={"total_ms": total_stream_dur, "ttft_ms": ttft_ms, "tokens": token_count}
                )
                self.trace_manager.complete_trace(
                    trace_id,
                    status="success",
                    summary=f"Consulta RAG resuelta con éxito en {total_stream_dur/1000:.2f}s ({len(citations)} citas generadas)."
                )
            except Exception as e:
                error_msg = str(e).lower()
                if "context size" in error_msg or "exceeds" in error_msg or "400" in error_msg:
                    self.trace_manager.add_step(
                        trace_id,
                        step_name="Fallback por Exceso de Contexto",
                        details="Activando fallback con contexto resumido",
                        status="warning"
                    )
                    fallback_stream = self.ollama_client.chat(
                        model=VISION_MODEL,
                        messages=[
                            {"role": "system", "content": "Responde de forma concisa en español."},
                            {"role": "user", "content": f"Contexto:\n{context_str[:600]}\n\nPregunta: {user_query}"}
                        ],
                        options=VISION_OPTIONS,
                        stream=True
                    )
                    for chunk in fallback_stream:
                        content = chunk.message.content
                        if content:
                            yield content
                    self.trace_manager.complete_trace(
                        trace_id,
                        status="success",
                        summary="Consulta completada mediante fallback de contexto condensado."
                    )
                else:
                    self.trace_manager.add_step(
                        trace_id,
                        step_name="Error en Generación LLM",
                        details=str(e),
                        status="error"
                    )
                    self.trace_manager.complete_trace(
                        trace_id,
                        status="error",
                        summary=f"Error durante inferencia LLM: {str(e)}"
                    )
                    yield f"\n\n*(Aviso de consulta: {str(e)})*"

        return stream_generator(), citations
