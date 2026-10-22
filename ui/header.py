"""
Header UI — Órgano Cefálico de la Criatura Líquida.
Tipografía gigante recortada, cromo vivo, texto curvado en SVG textPath y anotaciones en Instrument Serif cursiva.
"""
import streamlit as st
from core.media_types import get_media_icon
from core.liquid_theme import get_living_chrome_svg


def render_header(active_notebook, active_doc_names):
    """Renderiza el órgano cefálico de la criatura sin barra superior estándar."""
    is_trace = st.session_state.get("show_traceability", False)
    is_viewer_open = st.session_state.get("viewer_open", False)
    
    # 1. Titular gigante recortado contra los bordes de la pantalla (Actitud vanguardista)
    st.markdown(
        '<div class="titular-gigante speed-meltable">'
        '<span>CRIATURA LÍQUIDA</span>'
        '<span class="accent-orange">//</span>'
        '<span>LABORATORIO MULTIMODAL</span>'
        '<span class="accent-lime">●</span>'
        '<span>QWEN2.5-VL</span>'
        '<span class="accent-orange">//</span>'
        '<span>EMBEDDING-GEMMA</span>'
        '</div>',
        unsafe_allow_html=True
    )

    # 2. Órgano de Cromo Vivo Central con texto curvado en SVG textPath
    st.markdown(
        '<div style="position:relative; margin-bottom: 0.6rem;">'
        + get_living_chrome_svg() +
        '<div style="text-align:center; margin-top:-10px;">'
        '<svg width="420" height="32" viewBox="0 0 420 32" style="max-width:100%;">'
        '<path id="headerCurve" d="M 20,24 Q 210,5 400,24" fill="transparent"/>'
        '<text fill="#CFD8DA" font-family="Instrument Serif" font-style="italic" font-size="14" letter-spacing="2" opacity="0.75">'
        '<textPath href="#headerCurve" startOffset="50%" text-anchor="middle">'
        '« todo tiene masa, inercia y viscosidad · los especímenes se funden en el abismo »'
        '</textPath>'
        '</text>'
        '</svg>'
        '</div>'
        '</div>',
        unsafe_allow_html=True
    )

    # 3. Fila de Control Orgánico (Zona de interacción funcional limpia)
    col_meta, col_actions = st.columns([3.2, 1.8], gap="medium")

    with col_meta:
        pills_html = _build_liquid_doc_pills(active_doc_names)
        model_pill = _build_liquid_model_badge()
        st.markdown(
            f'<div style="display:flex; flex-direction:column; gap:4px;">'
            f'<div style="display:flex; align-items:baseline; gap:10px; flex-wrap:wrap;">'
            f'<span class="whisper-text" style="font-size:1.15rem; color:var(--naranja);">Organismo activo:</span>'
            f'<h2 style="font-size:1.6rem; letter-spacing:-0.03em; color:var(--mercurio); display:inline;">'
            f'{active_notebook.get("title", "Cuaderno")}</h2>'
            f'{model_pill}'
            f'</div>'
            f'<div style="margin-top:4px;">{pills_html}</div>'
            f'</div>',
            unsafe_allow_html=True
        )

    with col_actions:
        c1, c2 = st.columns(2, gap="small")
        with c1:
            trace_label = "💬 Modo Diálogo" if is_trace else "⚡ Sinapsis (Telemetría)"
            if st.button(trace_label, key="toggle_header_traceability", use_container_width=True):
                st.session_state.show_traceability = not is_trace
                st.rerun()

        with c2:
            if active_doc_names and not is_trace:
                viewer_label = "✕ Cerrar Ojo" if is_viewer_open else "👁️ Abrir Ojo (Visor)"
                if st.button(viewer_label, key="toggle_main_viewer", use_container_width=True):
                    st.session_state.viewer_open = not is_viewer_open
                    st.rerun()


def _build_liquid_doc_pills(active_doc_names):
    """Construye las píldoras de especímenes vinculados con brillo reactivo."""
    if not active_doc_names:
        return (
            '<span class="whisper-text" style="font-size:0.92rem; opacity:0.65;">'
            '(Sin especímenes absorbidos · Alimenta a la criatura en el panel lateral)'
            '</span>'
        )

    parts = []
    for d in active_doc_names:
        icon = get_media_icon(d)
        short = d[:22] + ("…" if len(d) > 22 else "")
        parts.append(
            f'<span class="organ-badge active-lime" style="font-size:0.75rem; margin-right:6px;">'
            f'{icon} {short}'
            f'</span>'
        )
    return "".join(parts)


def _build_liquid_model_badge():
    """Etiqueta cromada del motor de inferencia activo."""
    mode = st.session_state.get("llm_mode", "local")
    if mode == "cloud":
        prov = st.session_state.get("cloud_provider", "groq").upper()
        model = st.session_state.get("cloud_model", "cloud")
        return (
            f'<span class="organ-badge active-orange">'
            f'☁️ {prov} · {model[:14]}'
            f'</span>'
        )
    return (
        f'<span class="organ-badge active-lime">'
        f'🖥️ GPU QWEN2.5-VL · 8K CTX'
        f'</span>'
    )
