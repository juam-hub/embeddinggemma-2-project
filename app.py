"""
Criatura Líquida — RAG Multimodal Local (Qwen2.5-VL + EmbeddingGemma-2)
Laboratorio de Vanguardia: interfaz biomórfica con masa, inercia y viscosidad.
"""
import streamlit as st
import streamlit.components.v1 as components

from core.config import DATA_DIR
from core.stats_manager import StatsManager
from core.vector_store import VectorStore
from core.visual_analyzer import VisualAnalyzer
from core.pdf_extractor import PDFExtractor
from core.audio_processor import AudioProcessor
from core.video_processor import VideoProcessor
from core.rag_engine import RAGEngine
from core.notebook_manager import NotebookManager
from core.liquid_theme import get_liquid_creature_css, get_liquid_creature_js

from ui.state import init_session_state
from ui.sidebar import render_sidebar
from ui.header import render_header
from ui.chat import render_chat
from ui.viewer import render_viewer

# ── Configuración del Laboratorio ────────────────────────────────────
st.set_page_config(
    page_title="Criatura Líquida — RAG Multimodal",
    page_icon="🧪",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Inyección del Sistema de Diseño Líquido (CSS + JS Engine) ────────
st.markdown(get_liquid_creature_css(), unsafe_allow_html=True)
components.html(get_liquid_creature_js(), height=0)

# ── Rutas del sistema ────────────────────────────────────────────────
UPLOADS_DIR = DATA_DIR / "uploads"
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)

# ── Motores del Núcleo RAG (Persistentes) ─────────────────────────────
@st.cache_resource
def _init_rag_engine():
    audio_proc = AudioProcessor()
    vis_analyzer = VisualAnalyzer()
    video_proc = VideoProcessor(audio_processor=audio_proc, visual_analyzer=vis_analyzer)
    return RAGEngine(
        vector_store=VectorStore(),
        stats_manager=StatsManager(),
        visual_analyzer=vis_analyzer,
        pdf_extractor=PDFExtractor(),
        audio_processor=audio_proc,
        video_processor=video_proc,
    )

rag_engine = _init_rag_engine()
stats_manager = rag_engine.stats_manager
notebook_mgr = NotebookManager()

# ── Estado del Organismo ──────────────────────────────────────────────
active_id, active_notebook, active_doc_names = init_session_state(notebook_mgr)

# ── Vientre Ingestor Lateral ──────────────────────────────────────────
render_sidebar(notebook_mgr, stats_manager, rag_engine, UPLOADS_DIR)

# Actualizar referencias por si el vientre cambió el estado del cuaderno
active_id = st.session_state.notebook_data["active_id"]
active_notebook = st.session_state.notebook_data["notebooks"][active_id]
active_doc_names = active_notebook.get("doc_names", [])

# ── Órgano Cefálico (Header sin barra estándar) ───────────────────────
render_header(active_notebook, active_doc_names)

# ── Vistas Principales: Telemetría Sináptica vs. Diálogo + Ojo Visor ──
if st.session_state.get("show_traceability", False):
    from ui.traceability_view import render_traceability_view
    render_traceability_view(rag_engine, stats_manager)
else:
    viewer_active = (
        st.session_state.get("viewer_open", False) and bool(active_doc_names)
    )

    if viewer_active:
        col_chat, col_viewer = st.columns([1.15, 0.85], gap="medium")
    else:
        col_chat = st.container()
        col_viewer = None

    with col_chat:
        render_chat(rag_engine, notebook_mgr, active_id,
                    active_notebook, active_doc_names)

    if viewer_active and col_viewer is not None:
        with col_viewer:
            render_viewer(active_doc_names, stats_manager)

# ── Filamentos Biomórficos Decorativos en el Abismo ──────────────────
st.markdown(
    '<div style="position:fixed; bottom:-20px; left:20px; pointer-events:none; opacity:0.18; z-index:0;">'
    '<svg width="240" height="200" viewBox="0 0 240 200" fill="none" xmlns="http://www.w3.org/2000/svg">'
    '<path d="M 20,180 Q 90,60 180,140 T 230,40" stroke="#CFD8DA" stroke-width="2.5" stroke-dasharray="4 6"/>'
    '<path d="M 40,195 Q 110,80 160,160 T 210,60" stroke="#FF5B14" stroke-width="2"/>'
    '<circle cx="180" cy="140" r="4" fill="#C6FF3D"/>'
    '<circle cx="90" cy="60" r="3" fill="#FF5B14"/>'
    '</svg>'
    '</div>',
    unsafe_allow_html=True,
)
