"""
Viewer UI — Órgano Ocular / Visor de Especímenes Multimedia.
Proyección de folios PDF a 150 DPI con resaltes venenosos, fotogramas de video e intervalos sonoros.
"""
import streamlit as st
from pathlib import Path

from core.document_viewer import (
    render_document_view,
    resolve_document_path,
    get_document_page_count,
)
from core.media_types import (
    get_media_type,
    get_media_icon,
    format_timestamp,
)
from ui.state import reset_viewer


def render_viewer(active_doc_names, stats_manager):
    """Renderiza el órgano ocular de la criatura."""
    st.markdown('<div class="creature-organ speed-meltable">', unsafe_allow_html=True)

    _render_viewer_header()
    curr_doc = _render_doc_switcher(active_doc_names)
    _render_document_content(curr_doc, active_doc_names, stats_manager)

    st.markdown("</div>", unsafe_allow_html=True)


def _render_viewer_header():
    """Barra del Órgano Ocular con botón de retracción."""
    c_title, c_close = st.columns([4, 1], gap="small")
    with c_title:
        st.markdown(
            '<div style="display:flex; align-items:center; gap:8px;">'
            '<span style="font-size:1.2rem;">👁️</span>'
            '<span style="font-weight:800; font-size:0.92rem; letter-spacing:0.04em; text-transform:uppercase; color:var(--mercurio);">'
            'Órgano Ocular // Visor'
            '</span>'
            '</div>',
            unsafe_allow_html=True,
        )
    with c_close:
        if st.button("✕", key="btn_close_viewer", help="Retraer visor"):
            st.session_state.viewer_open = False
            st.rerun()


def _render_doc_switcher(active_doc_names):
    """Selector de espécimen visual o multimedia en exhibición."""
    curr_doc = st.session_state.get("current_view_doc", active_doc_names[0])
    if curr_doc not in active_doc_names:
        curr_doc = active_doc_names[0]
        st.session_state.current_view_doc = curr_doc

    if len(active_doc_names) > 1:
        idx = active_doc_names.index(curr_doc)
        selected = st.selectbox(
            "Espécimen enfocado:",
            options=active_doc_names,
            index=idx,
            label_visibility="collapsed",
        )
        if selected != curr_doc:
            reset_viewer(doc_name=selected)
            st.rerun()
        return selected

    icon = get_media_icon(curr_doc)
    st.markdown(
        f'<div class="organ-badge active-lime" style="margin-top:6px; margin-bottom:10px;">'
        f"{icon} {curr_doc}</div>",
        unsafe_allow_html=True,
    )
    return curr_doc


def _render_document_content(curr_doc, active_doc_names, stats_manager):
    """Resuelve la ruta física y proyecta la vista según el tipo de medio."""
    doc_path = resolve_document_path(curr_doc)
    if not doc_path or not doc_path.exists():
        st.error(f"No se localizó el espécimen físico '{curr_doc}'.")
        return

    m_type = get_media_type(curr_doc)

    # 1. ESPECTRO DE AUDIO
    if m_type == "audio":
        _render_audio_view(doc_path, curr_doc, stats_manager)
        return

    # 2. ESPECTRO DE VIDEO
    if m_type == "video":
        _render_video_view(doc_path, curr_doc, stats_manager)
        return

    # 3. FOLIO PDF O IMAGEN
    total_pages = get_document_page_count(doc_path)
    curr_page = max(1, min(total_pages, st.session_state.get("current_view_page", 1)))

    if total_pages > 1:
        c_prev, c_label, c_next = st.columns([1, 2.5, 1], gap="small")
        with c_prev:
            if st.button("◀", key="btn_prev_page", disabled=(curr_page <= 1), use_container_width=True):
                reset_viewer(page=curr_page - 1)
                st.rerun()
        with c_label:
            st.markdown(
                f'<div style="text-align:center; padding-top:6px; font-weight:700; font-size:0.85rem; color:var(--mercurio);">'
                f'Folio <span style="color:var(--naranja);">{curr_page}</span> de {total_pages}</div>',
                unsafe_allow_html=True
            )
        with c_next:
            if st.button("▶", key="btn_next_page", disabled=(curr_page >= total_pages), use_container_width=True):
                reset_viewer(page=curr_page + 1)
                st.rerun()

    # Proyección gráfica del pliego a 150 DPI
    snippet = st.session_state.get("current_view_snippet", "")
    element_id = st.session_state.get("current_view_element_id", "")

    try:
        png_bytes, highlighted, extracted_img_path = render_document_view(
            file_path=doc_path,
            page_number=curr_page,
            snippet_text=snippet,
            element_id=element_id
        )

        if highlighted:
            st.markdown(
                '<div class="organ-badge active-orange" style="margin:6px 0;">'
                '⚡ EVIDENCIA FOCALIZADA EN PLIEGO'
                '</div>',
                unsafe_allow_html=True
            )

        st.image(png_bytes, use_container_width=True)

        # Si se extrajo una imagen aislada o figura
        if extracted_img_path and Path(extracted_img_path).exists():
            st.markdown(
                '<div class="whisper-text" style="font-size:0.85rem; margin-top:8px; color:var(--lima);">'
                'Elemento visual aislado de alta resolución:</div>',
                unsafe_allow_html=True
            )
            st.image(extracted_img_path, width=280)

    except Exception as e:
        st.error(f"Fallo en la proyección del espécimen: {e}")


def _render_audio_view(doc_path: Path, doc_name: str, stats_manager):
    """Visor sonoro con reproductor nativo y marcas temporales."""
    st.audio(str(doc_path))

    target_start = st.session_state.get("current_view_start_time", 0.0)
    target_lbl = st.session_state.get("current_view_timestamp_label", "")

    if target_lbl:
        st.markdown(
            f'<div class="organ-badge active-lime" style="margin:8px 0;">'
            f'⏱️ INTERVALO FOCALIZADO: {target_lbl}'
            f'</div>',
            unsafe_allow_html=True
        )

    stats = stats_manager.get_document_stats(doc_name) or {}
    segments = stats.get("segments", [])

    if segments:
        st.markdown(
            '<div class="whisper-text" style="font-size:0.85rem; margin-top:10px; margin-bottom:6px; color:var(--mercurio);">'
            'Segmentos de habla transcritos:</div>',
            unsafe_allow_html=True
        )
        for seg in segments[:8]:
            is_active = (abs(seg["start_time"] - target_start) < 2.0)
            border_col = "var(--lima)" if is_active else "rgba(207,216,218,0.2)"
            bg_col = "rgba(198,255,61,0.1)" if is_active else "rgba(6,26,32,0.8)"
            snippet = seg.get("raw_text") or seg.get("content") or ""
            preview = snippet[:120] + ("…" if len(snippet) > 120 else "")

            st.markdown(
                f'<div style="background:{bg_col}; border:1px solid {border_col}; border-radius:10px; padding:8px 12px; margin-bottom:6px; font-size:0.82rem;">'
                f'<span style="font-weight:700; color:var(--naranja); margin-right:6px;">⏱️ {seg["timestamp_label"]}</span>'
                f'<span style="color:var(--mercurio);">{preview}</span>'
                f'</div>',
                unsafe_allow_html=True
            )


def _render_video_view(doc_path: Path, doc_name: str, stats_manager):
    """Visor audiovisual con reproducción y fotogramas extraídos."""
    st.video(str(doc_path))

    target_lbl = st.session_state.get("current_view_timestamp_label", "")
    if target_lbl:
        st.markdown(
            f'<div class="organ-badge active-orange" style="margin:8px 0;">'
            f'🎬 ESCENA SELECCIONADA: {target_lbl}'
            f'</div>',
            unsafe_allow_html=True
        )

    stats = stats_manager.get_document_stats(doc_name) or {}
    elements = stats.get("elements", [])

    if elements:
        st.markdown(
            '<div class="whisper-text" style="font-size:0.85rem; margin-top:10px; margin-bottom:6px; color:var(--mercurio);">'
            'Fotogramas analizados por Qwen2.5-VL:</div>',
            unsafe_allow_html=True
        )
        for elem in elements[:4]:
            t_lbl = elem.get("timestamp_label") or format_timestamp(elem.get("start_time", 0.0))
            st.markdown(
                f'<div style="background:rgba(6,26,32,0.85); border:1px solid rgba(207,216,218,0.2); border-radius:12px; padding:10px; margin-bottom:8px;">'
                f'<div style="display:flex; justify-content:space-between; margin-bottom:6px;">'
                f'<span style="font-weight:700; color:var(--naranja); font-size:0.8rem;">⏱️ {t_lbl}</span>'
                f'<span class="organ-badge active-lime" style="font-size:0.65rem;">{elem.get("visual_category", "Escena")}</span>'
                f'</div>'
                f'<div class="whisper-text" style="font-size:0.8rem; color:var(--mercurio); line-height:1.4;">{elem.get("description", "")[:140]}…</div>'
                f'</div>',
                unsafe_allow_html=True
            )
