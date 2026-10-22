import sqlite3
import json
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
from core.config import DB_PATH
from core.media_types import format_timestamp, format_time_interval


class StatsManager:
    def __init__(self, db_path: Path = DB_PATH):
        self.db_path = str(db_path)
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS documents (
                    doc_name TEXT PRIMARY KEY,
                    file_path TEXT,
                    media_type TEXT DEFAULT 'pdf',
                    duration REAL DEFAULT 0.0,
                    duration_str TEXT DEFAULT '',
                    total_pages INTEGER DEFAULT 0,
                    total_text_chunks INTEGER DEFAULT 0,
                    total_visual_elements INTEGER DEFAULT 0,
                    total_charts INTEGER DEFAULT 0,
                    total_diagrams INTEGER DEFAULT 0,
                    total_tables INTEGER DEFAULT 0,
                    total_photos INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS visual_elements (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    doc_name TEXT,
                    element_id TEXT UNIQUE,
                    page_number INTEGER,
                    start_time REAL DEFAULT 0.0,
                    end_time REAL DEFAULT 0.0,
                    timestamp_label TEXT DEFAULT '',
                    element_type TEXT,
                    visual_category TEXT DEFAULT 'Pendiente',
                    image_path TEXT,
                    width INTEGER,
                    height INTEGER,
                    description TEXT,
                    transcribed_text TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (doc_name) REFERENCES documents(doc_name) ON DELETE CASCADE
                )
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS media_segments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    doc_name TEXT,
                    chunk_id TEXT UNIQUE,
                    start_time REAL DEFAULT 0.0,
                    end_time REAL DEFAULT 0.0,
                    timestamp_label TEXT DEFAULT '',
                    content TEXT,
                    raw_text TEXT,
                    source_type TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (doc_name) REFERENCES documents(doc_name) ON DELETE CASCADE
                )
            """)

            # Safe column migrations for existing databases
            cursor.execute("PRAGMA table_info(documents)")
            doc_cols = [row["name"] for row in cursor.fetchall()]
            if "media_type" not in doc_cols:
                cursor.execute("ALTER TABLE documents ADD COLUMN media_type TEXT DEFAULT 'pdf'")
            if "duration" not in doc_cols:
                cursor.execute("ALTER TABLE documents ADD COLUMN duration REAL DEFAULT 0.0")
            if "duration_str" not in doc_cols:
                cursor.execute("ALTER TABLE documents ADD COLUMN duration_str TEXT DEFAULT ''")

            cursor.execute("PRAGMA table_info(visual_elements)")
            vis_cols = [row["name"] for row in cursor.fetchall()]
            if "start_time" not in vis_cols:
                cursor.execute("ALTER TABLE visual_elements ADD COLUMN start_time REAL DEFAULT 0.0")
            if "end_time" not in vis_cols:
                cursor.execute("ALTER TABLE visual_elements ADD COLUMN end_time REAL DEFAULT 0.0")
            if "timestamp_label" not in vis_cols:
                cursor.execute("ALTER TABLE visual_elements ADD COLUMN timestamp_label TEXT DEFAULT ''")

            conn.commit()

    def register_document(
        self,
        doc_name: str,
        file_path: str,
        total_pages: int = 1,
        media_type: str = "pdf",
        duration: float = 0.0,
        duration_str: str = ""
    ):
        if not duration_str and duration > 0.0:
            duration_str = format_timestamp(duration)

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO documents (
                    doc_name, file_path, media_type, duration, duration_str,
                    total_pages, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(doc_name) DO UPDATE SET
                    file_path=excluded.file_path,
                    media_type=excluded.media_type,
                    duration=excluded.duration,
                    duration_str=excluded.duration_str,
                    total_pages=excluded.total_pages,
                    created_at=excluded.created_at
            """, (
                doc_name, file_path, media_type, duration, duration_str,
                total_pages, datetime.now().isoformat()
            ))
            # Remove previous elements and segments if re-uploading
            cursor.execute("DELETE FROM visual_elements WHERE doc_name = ?", (doc_name,))
            cursor.execute("DELETE FROM media_segments WHERE doc_name = ?", (doc_name,))
            conn.commit()

    def add_visual_element(
        self,
        doc_name: str,
        element_id: str,
        page_number: int,
        element_type: str,
        image_path: str,
        width: int,
        height: int,
        start_time: float = 0.0,
        end_time: float = 0.0,
        timestamp_label: str = ""
    ):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO visual_elements (
                    doc_name, element_id, page_number, start_time, end_time,
                    timestamp_label, element_type, image_path, width, height
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(element_id) DO UPDATE SET
                    page_number=excluded.page_number,
                    start_time=excluded.start_time,
                    end_time=excluded.end_time,
                    timestamp_label=excluded.timestamp_label,
                    element_type=excluded.element_type,
                    image_path=excluded.image_path,
                    width=excluded.width,
                    height=excluded.height
            """, (
                doc_name, element_id, page_number, start_time, end_time,
                timestamp_label, element_type, image_path, width, height
            ))
            conn.commit()

    def update_visual_element_analysis(
        self,
        element_id: str,
        visual_category: str,
        description: str,
        transcribed_text: str = ""
    ):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE visual_elements
                SET visual_category = ?, description = ?, transcribed_text = ?
                WHERE element_id = ?
            """, (visual_category, description, transcribed_text, element_id))
            conn.commit()

    def add_media_segment(
        self,
        doc_name: str,
        chunk_id: str,
        start_time: float,
        end_time: float,
        timestamp_label: str,
        content: str,
        raw_text: str,
        source_type: str
    ):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO media_segments (
                    doc_name, chunk_id, start_time, end_time,
                    timestamp_label, content, raw_text, source_type
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(chunk_id) DO UPDATE SET
                    start_time=excluded.start_time,
                    end_time=excluded.end_time,
                    timestamp_label=excluded.timestamp_label,
                    content=excluded.content,
                    raw_text=excluded.raw_text,
                    source_type=excluded.source_type
            """, (
                doc_name, chunk_id, start_time, end_time,
                timestamp_label, content, raw_text, source_type
            ))
            conn.commit()

    def get_media_segments(self, doc_name: str) -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT chunk_id, doc_name, start_time, end_time,
                       timestamp_label, content, raw_text, source_type, created_at
                FROM media_segments
                WHERE doc_name = ?
                ORDER BY start_time ASC
            """, (doc_name,))
            return [dict(r) for r in cursor.fetchall()]

    def delete_document(self, doc_name: str):
        """Removes all metadata, visual elements, and media segments for a document from SQLite."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM visual_elements WHERE doc_name = ?", (doc_name,))
            cursor.execute("DELETE FROM media_segments WHERE doc_name = ?", (doc_name,))
            cursor.execute("DELETE FROM documents WHERE doc_name = ?", (doc_name,))
            conn.commit()

    def delete_all_documents(self):
        """Removes all registered documents and segments from SQLite."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM visual_elements")
            cursor.execute("DELETE FROM media_segments")
            cursor.execute("DELETE FROM documents")
            conn.commit()

    def get_visual_element(self, element_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves details of a single visual element by its ID."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT element_id, doc_name, page_number, start_time, end_time,
                       timestamp_label, element_type, visual_category,
                       image_path, width, height, description, transcribed_text, created_at
                FROM visual_elements
                WHERE element_id = ?
            """, (element_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def update_document_summary(self, doc_name: str, total_text_chunks: int):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT visual_category, COUNT(*) as count
                FROM visual_elements
                WHERE doc_name = ?
                GROUP BY visual_category
            """, (doc_name,))
            rows = cursor.fetchall()

            counts = {
                "Gráfico estadístico": 0,
                "Diagrama": 0,
                "Tabla visual": 0,
                "Fotografía/Ilustración": 0
            }
            total_visual = 0
            for r in rows:
                cat = r["visual_category"]
                c = r["count"]
                total_visual += c
                matched = False
                for key in counts.keys():
                    if key.lower() in cat.lower() or cat.lower() in key.lower():
                        counts[key] += c
                        matched = True
                        break
                if not matched:
                    counts["Fotografía/Ilustración"] += c

            cursor.execute("""
                UPDATE documents
                SET total_text_chunks = ?,
                    total_visual_elements = ?,
                    total_charts = ?,
                    total_diagrams = ?,
                    total_tables = ?,
                    total_photos = ?
                WHERE doc_name = ?
            """, (
                total_text_chunks,
                total_visual,
                counts["Gráfico estadístico"],
                counts["Diagrama"],
                counts["Tabla visual"],
                counts["Fotografía/Ilustración"],
                doc_name
            ))
            conn.commit()

    def get_document_stats(self, doc_name: str) -> Optional[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM documents WHERE doc_name = ?", (doc_name,))
            doc = cursor.fetchone()
            if not doc:
                return None

            cursor.execute("""
                SELECT element_id, page_number, start_time, end_time, timestamp_label,
                       element_type, visual_category, image_path, width, height,
                       description, transcribed_text
                FROM visual_elements
                WHERE doc_name = ?
                ORDER BY start_time ASC, page_number ASC, id ASC
            """, (doc_name,))
            elements = [dict(r) for r in cursor.fetchall()]

            cursor.execute("""
                SELECT chunk_id, start_time, end_time, timestamp_label,
                       content, raw_text, source_type
                FROM media_segments
                WHERE doc_name = ?
                ORDER BY start_time ASC
            """, (doc_name,))
            segments = [dict(r) for r in cursor.fetchall()]

            data = dict(doc)
            data["elements"] = elements
            data["segments"] = segments

            # Page or timestamp breakdown map
            page_map = {}
            for elem in elements:
                p = elem["page_number"]
                if p not in page_map:
                    page_map[p] = []
                page_map[p].append({
                    "id": elem["element_id"],
                    "category": elem["visual_category"],
                    "path": elem["image_path"],
                    "timestamp_label": elem.get("timestamp_label", "")
                })
            data["page_map"] = page_map
            return data

    def list_all_documents(self) -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT doc_name, media_type, duration_str, total_pages,
                       total_visual_elements, created_at
                FROM documents
                ORDER BY created_at DESC
            """)
            return [dict(r) for r in cursor.fetchall()]

    def format_stats_sheet(self, doc_names: Any) -> str:
        """
        Generates the Global Statistical Technical Sheet for injection into System Prompt.
        Supports single or multiple documents of types: PDF, standalone images, audio, and video.
        """
        if isinstance(doc_names, str):
            names = [doc_names]
        elif isinstance(doc_names, (list, tuple, set)):
            names = [n for n in doc_names if n]
        else:
            names = []

        if not names:
            return "No se ha indexado ningún documento todavía."

        if len(names) == 1:
            stats = self.get_document_stats(names[0])
            if not stats:
                return f"No se encontraron estadísticas para {names[0]}."

            m_type = stats.get("media_type", "pdf")

            if m_type == "audio":
                lines = [
                    "================ FICHA TÉCNICA DE ESPÉCIMEN DE AUDIO ================",
                    f"• Nombre del archivo: {stats['doc_name']}",
                    f"• Formato: Registro sonoro / Grabación de audio",
                    f"• Duración total: {stats.get('duration_str', 'Desconocida')} ({stats.get('duration', 0.0):.1f} segundos)",
                    f"• Total de segmentos transcritos: {len(stats.get('segments', []))}",
                    "• Desglose cronológico de intervalos sonoros:"
                ]
                for seg in stats.get("segments", [])[:8]:
                    snippet = seg.get("raw_text", "").strip()
                    if snippet:
                        snippet_preview = snippet[:60] + ("…" if len(snippet) > 60 else "")
                        lines.append(f"  - [{seg['timestamp_label']}]: \"{snippet_preview}\"")
                    else:
                        lines.append(f"  - [{seg['timestamp_label']}]: (Silencio / Música / Sonido ambiente)")
                if len(stats.get("segments", [])) > 8:
                    lines.append(f"  - ... y otros {len(stats.get('segments', [])) - 8} segmentos adicionales.")
                lines.append("======================================================================")
                lines.append("REGLA DE CITACIÓN PARA AUDIO: Al referenciar datos o declaraciones de este audio,")
                lines.append("DEBES citar SIEMPRE el lapso de tiempo exacto (ej. [⏱️ 01:23 - 01:38]).")
                lines.append("======================================================================")
                return "\n".join(lines)

            if m_type == "video":
                lines = [
                    "================ FICHA TÉCNICA DE ESPÉCIMEN DE VIDEO ================",
                    f"• Nombre del archivo: {stats['doc_name']}",
                    f"• Formato: Archivo audiovisual (video con pista de audio y fotogramas)",
                    f"• Duración total: {stats.get('duration_str', 'Desconocida')} ({stats.get('duration', 0.0):.1f} segundos)",
                    f"• Fotogramas visuales analizados: {stats['total_visual_elements']}",
                    f"• Segmentos de habla transcritos: {len(stats.get('segments', []))}",
                    "• Desglose de fotogramas visuales (análisis de pantalla / escena):"
                ]
                for elem in stats.get("elements", [])[:6]:
                    t_lbl = elem.get("timestamp_label") or format_timestamp(elem.get("start_time", 0.0))
                    desc_prev = elem.get("description", "")[:60]
                    lines.append(f"  - [{t_lbl}] {elem['visual_category']}: {desc_prev}…")
                lines.append("• Desglose de habla y audio (lo que se escucha):")
                for seg in stats.get("segments", [])[:6]:
                    snippet = seg.get("raw_text", "").strip()
                    if snippet:
                        snippet_prev = snippet[:60] + ("…" if len(snippet) > 60 else "")
                        lines.append(f"  - [{seg['timestamp_label']}]: \"{snippet_prev}\"")
                lines.append("======================================================================")
                lines.append("REGLA DE CITACIÓN PARA VIDEO: Al referenciar lo que se observa o se escucha en el video,")
                lines.append("DEBES citar SIEMPRE el lapso de tiempo exacto (ej. [⏱️ 01:15 - 01:30]).")
                lines.append("Indica explícitamente si la evidencia proviene de lo que se visualiza o de lo que se escucha.")
                lines.append("======================================================================")
                return "\n".join(lines)

            # Default PDF / Image formatting
            lines = [
                "================ FICHA TÉCNICA Y ESTADÍSTICA GLOBAL DEL DOCUMENTO ================",
                f"• Nombre del archivo: {stats['doc_name']}",
                f"• Total de páginas: {stats['total_pages']}",
                f"• Total de fragmentos de texto: {stats['total_text_chunks']}",
                f"• Conteo exacto de elementos visuales extraídos: {stats['total_visual_elements']}",
                "• Desglose preciso por categoría visual:",
                f"  - Gráficos estadísticos / curvas / barras / tortas: {stats['total_charts']}",
                f"  - Diagramas / flujogramas / mapas conceptuales: {stats['total_diagrams']}",
                f"  - Tablas visuales / datos tabulares: {stats['total_tables']}",
                f"  - Fotografías / Ilustraciones generales: {stats['total_photos']}",
                "• Índice de ubicación de elementos visuales por página:"
            ]
            if not stats["page_map"]:
                lines.append("  (No se encontraron elementos visuales mayores a 120x120 px)")
            else:
                for page, elems in sorted(stats["page_map"].items()):
                    elem_summary = ", ".join([f"{e['category']} (ID: {e['id']})" for e in elems])
                    lines.append(f"  - Página {page}: {len(elems)} elemento(s) [{elem_summary}]")
            lines.append("================================================================================")
            lines.append("REGLA ESTRICTA DE CONTEO: Si el usuario te pregunta cuántas imágenes, fotos,")
            lines.append("gráficos o diagramas hay en total o en páginas específicas, DEBES responder")
            lines.append("usando EXACTAMENTE los números de esta Ficha Técnica Global, nunca adivines.")
            lines.append("================================================================================")
            return "\n".join(lines)

        # Multiple documents associated with the notebook
        lines = [
            "================ FICHA TÉCNICA Y ESTADÍSTICA GLOBAL DE LOS DOCUMENTOS ASOCIADOS ================",
            f"Este cuaderno tiene {len(names)} pliegos/archivos asociados bajo consulta prioritaria."
        ]
        grand_total_pages = 0
        grand_total_visual = 0
        grand_total_audio_sec = 0.0

        for name in names:
            stats = self.get_document_stats(name)
            if not stats:
                continue
            m_type = stats.get("media_type", "pdf")

            if m_type in {"audio", "video"}:
                grand_total_audio_sec += stats.get("duration", 0.0)
                grand_total_visual += stats.get("total_visual_elements", 0)
                icon = "🎬" if m_type == "video" else "🎵"
                lines.append(f"\n--- {icon} {m_type.upper()}: {stats['doc_name']} ---")
                lines.append(f"• Duración: {stats.get('duration_str', 'N/A')} | Segmentos: {len(stats.get('segments', []))} | Cuadros visuales: {stats['total_visual_elements']}")
            else:
                grand_total_pages += stats["total_pages"]
                grand_total_visual += stats["total_visual_elements"]
                icon = "🖼️" if m_type == "image" else "📄"
                lines.append(f"\n--- {icon} DOCUMENTO: {stats['doc_name']} ---")
                lines.append(f"• Páginas: {stats['total_pages']} | Elementos visuales: {stats['total_visual_elements']}")
                lines.append(f"• Desglose: Gráficos={stats['total_charts']}, Diagramas={stats['total_diagrams']}, Tablas={stats['total_tables']}, Fotos={stats['total_photos']}")

        lines.append("\n=== REGLAS GLOBALES DE CITAS Y TIEMPOS ===")
        lines.append("• Para pliegos PDF cita las páginas (ej. [Página 3]).")
        lines.append("• Para archivos de audio y video cita SIEMPRE el lapso de tiempo exacto (ej. [⏱️ 01:23 - 01:45]).")
        lines.append("================================================================================")
        return "\n".join(lines)
