"""
Sidebar UI — Vientre Ingestor / Gabinete de Especímenes Multimedia.
Control del motor de inferencia (Local GPU vs. Nube API), gestión de cuadernos y absorción de archivos.
"""
import streamlit as st
from pathlib import Path

from core.media_types import (
    get_media_type,
    get_media_icon,
    ALL_SUPPORTED_EXTENSIONS,
)
from ui.state import reset_viewer
from core.cloud_llm import CLOUD_PROVIDERS, test_cloud_connection


def render_sidebar(notebook_mgr, stats_manager, rag_engine, uploads_dir):
    """Renderiza el vientre ingestor lateral con control de hardware, cuadernos y archivos."""
    active_id = st.session_state.notebook_data["active_id"]
    active_notebook = st.session_state.notebook_data["notebooks"][active_id]
    active_doc_names = active_notebook.get("doc_names", [])

    with st.sidebar:
        _render_organ_badge()
        _render_llm_switcher()
        _render_hardware_plate()
        
        st.markdown("<hr style='border-color:rgba(207,216,218,0.15); margin:12px 0;'>", unsafe_allow_html=True)
        
        # 1. GESTIÓN DE CUADERNOS / ORGANISMOS
        _render_notebook_section(notebook_mgr, active_id)

        st.markdown("<hr style='border-color:rgba(207,216,218,0.15); margin:12px 0;'>", unsafe_allow_html=True)

        # 2. ABSORCIÓN DE ESPECÍMENES (UPLOADER MULTIMODAL)
        _render_upload_section(notebook_mgr, stats_manager, rag_engine,
                               active_id, active_doc_names, uploads_dir)

        st.markdown("<hr style='border-color:rgba(207,216,218,0.15); margin:12px 0;'>", unsafe_allow_html=True)

        # 3. ESPECÍMENES VINCULADOS AL CUADERNO
        _render_document_list(notebook_mgr, stats_manager, rag_engine,
                              active_id, active_doc_names, uploads_dir)

        # 4. BOTÓN DE PURGA DE CONVERSACIÓN
        if active_notebook.get("messages"):
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("🗑️ Vaciar Diálogo Neural", key=f"clear_msgs_{active_id}", use_container_width=True):
                notebook_mgr.update_notebook(active_id, {"messages": []})
                st.session_state.notebook_data = notebook_mgr.load_all()
                st.rerun()


def _render_organ_badge():
    """Etiqueta biomórfica de la criatura."""
    st.markdown(
        '<div style="background:rgba(6,26,32,0.9); border:1.5px solid var(--naranja); border-radius:14px; padding:10px 14px; margin-bottom:12px; box-shadow:0 0 15px rgba(255,91,20,0.2);">'
        '<div style="font-weight:800; font-size:0.95rem; letter-spacing:0.04em; color:var(--mercurio); display:flex; align-items:center; gap:8px;">'
        '<span>🧪</span> VIENTRE INGESTOR'
        '</div>'
        '<div class="whisper-text" style="font-size:0.75rem; color:var(--lima); margin-top:2px;">'
        'RAG Multimodal // Inercia & Viscosidad'
        '</div>'
        '</div>',
        unsafe_allow_html=True,
    )


def _render_hardware_plate():
    """Placa de estado del hardware objetivo en tiempo real."""
    st.markdown(
        '<div style="background:rgba(11,37,46,0.6); border:1px solid rgba(207,216,218,0.2); border-radius:10px; padding:8px 12px; margin-bottom:10px; font-size:0.75rem;">'
        '<div style="color:var(--mercurio); display:flex; justify-content:space-between; margin-bottom:3px;">'
        '<span>VISIÓN/CHAT (GPU):</span>'
        '<span style="color:var(--naranja); font-weight:700;">RTX 5050 8GB</span>'
        '</div>'
        '<div style="color:var(--mercurio); display:flex; justify-content:space-between;">'
        '<span>VECTORES (CPU):</span>'
        '<span style="color:var(--lima); font-weight:700;">Gemma-2 Aislada</span>'
        '</div>'
        '</div>',
        unsafe_allow_html=True
    )


def _render_llm_switcher():
    """Conmutador entre Local (Ollama GPU) y Nube (Groq, OpenAI, Gemini)."""
    st.markdown(
        '<div style="font-size:0.78rem; font-weight:800; letter-spacing:0.06em; text-transform:uppercase; color:var(--mercurio); margin-bottom:6px;">'
        '⚙️ MOTOR DE INFERENCIA:'
        '</div>',
        unsafe_allow_html=True
    )

    mode_options = ["🖥️ Local (GPU)", "☁️ Nube (API)"]
    curr_mode = st.session_state.get("llm_mode", "local")
    curr_idx = 0 if curr_mode == "local" else 1

    selected_mode = st.radio(
        "Modo de Inferencia",
        options=mode_options,
        index=curr_idx,
        key="radio_llm_mode",
        horizontal=True,
        label_visibility="collapsed"
    )

    new_mode = "local" if "Local" in selected_mode else "cloud"
    if new_mode != curr_mode:
        st.session_state.llm_mode = new_mode
        st.rerun()

    if new_mode == "cloud":
        with st.container():
            prov_keys = list(CLOUD_PROVIDERS.keys())
            saved_prov = st.session_state.get("cloud_provider", "groq")
            p_idx = prov_keys.index(saved_prov) if saved_prov in prov_keys else 0

            sel_prov = st.selectbox(
                "Proveedor en la Nube:",
                options=prov_keys,
                index=p_idx,
                format_func=lambda k: f"{CLOUD_PROVIDERS[k]['label']} ({CLOUD_PROVIDERS[k]['speed']})",
                key="sb_cloud_provider"
            )
            st.session_state.cloud_provider = sel_prov

            models = CLOUD_PROVIDERS[sel_prov]["models"]
            saved_m = st.session_state.get("cloud_model", models[0])
            m_idx = models.index(saved_m) if saved_m in models else 0

            sel_model = st.selectbox("Modelo:", options=models, index=m_idx, key="sb_cloud_model")
            st.session_state.cloud_model = sel_model

            api_key = st.text_input(
                "API Key secreta:",
                value=st.session_state.get("cloud_api_key", ""),
                type="password",
                help="La clave solo se almacena en memoria volátil de esta sesión",
                key="input_cloud_api_key"
            )
            st.session_state.cloud_api_key = api_key

            if st.button("🔌 Probar Conexión", key="btn_test_cloud"):
                with st.spinner("Verificando credenciales..."):
                    ok, msg = test_cloud_connection(sel_prov, api_key, sel_model)
                    if ok:
                        st.success(f"Conexión exitosa a {sel_prov.upper()}")
                    else:
                        st.error(msg)


def _render_notebook_section(notebook_mgr, active_id):
    """Gabinete de cuadernos de investigación."""
    st.markdown(
        '<div style="font-size:0.78rem; font-weight:800; letter-spacing:0.06em; text-transform:uppercase; color:var(--mercurio); margin-bottom:6px;">'
        '📂 ORGANISMOS / CUADERNOS:'
        '</div>',
        unsafe_allow_html=True
    )

    if st.button("➕ Nuevo Cuaderno", key="btn_new_nb", use_container_width=True):
        new_id = notebook_mgr.create_notebook()
        st.session_state.notebook_data = notebook_mgr.load_all()
        st.session_state.notebook_data["active_id"] = new_id
        notebook_mgr.save_all(st.session_state.notebook_data)
        st.rerun()

    notebooks = st.session_state.notebook_data.get("notebooks", {})
    for nb_id, nb in notebooks.items():
        is_active = (nb_id == active_id)
        border_col = "var(--naranja)" if is_active else "rgba(207,216,218,0.2)"
        bg_col = "rgba(255,91,20,0.12)" if is_active else "rgba(6,26,32,0.6)"

        c_btn, c_del = st.columns([4, 1], gap="small")
        with c_btn:
            title_label = f"● {nb['title']}" if is_active else f"○ {nb['title']}"
            if st.button(title_label, key=f"sel_nb_{nb_id}", use_container_width=True):
                st.session_state.notebook_data["active_id"] = nb_id
                notebook_mgr.save_all(st.session_state.notebook_data)
                st.rerun()

        with c_del:
            if len(notebooks) > 1 and st.button("✕", key=f"del_nb_{nb_id}", help="Eliminar cuaderno"):
                notebook_mgr.delete_notebook(nb_id)
                st.session_state.notebook_data = notebook_mgr.load_all()
                st.rerun()


def _render_upload_section(notebook_mgr, stats_manager, rag_engine,
                           active_id, active_doc_names, uploads_dir):
    """Zona de ingesta y desintegración vectorial de archivos."""
    st.markdown(
        '<div style="font-size:0.78rem; font-weight:800; letter-spacing:0.06em; text-transform:uppercase; color:var(--mercurio); margin-bottom:6px;">'
        '📥 ALIMENTAR ESPECÍMENES:'
        '</div>',
        unsafe_allow_html=True
    )

    raw_exts = [e.lstrip(".").upper() for e in ALL_SUPPORTED_EXTENSIONS]
    uploaded_files = st.file_uploader(
        "Arrastra o selecciona PDFs, imágenes, audios o videos:",
        type=list(ALL_SUPPORTED_EXTENSIONS),
        accept_multiple_files=True,
        key="uploader_multimedia"
    )

    if uploaded_files:
        for uf in uploaded_files:
            if uf.name in active_doc_names:
                continue

            target_path = uploads_dir / uf.name
            with open(target_path, "wb") as f:
                f.write(uf.getbuffer())

            prog_bar = st.progress(0.0)
            status_text = st.empty()

            def cb(p, msg):
                prog_bar.progress(p)
                status_text.text(msg)

            try:
                rag_engine.index_document(target_path, progress_callback=cb)
                notebook_mgr.add_document_to_notebook(active_id, uf.name)
                st.session_state.notebook_data = notebook_mgr.load_all()
                status_text.empty()
                prog_bar.empty()
                st.success(f"Absorbido: {uf.name}")
                st.rerun()
            except Exception as e:
                st.error(f"Fallo al procesar {uf.name}: {e}")


def _render_document_list(notebook_mgr, stats_manager, rag_engine,
                          active_id, active_doc_names, uploads_dir):
    """Lista de especímenes vinculados al cuaderno actual."""
    if not active_doc_names:
        return

    st.markdown(
        f'<div style="font-size:0.78rem; font-weight:800; letter-spacing:0.06em; text-transform:uppercase; color:var(--mercurio); margin-bottom:6px;">'
        f'🧬 ESPECÍMENES DEL ORGANISMO ({len(active_doc_names)}):'
        f'</div>',
        unsafe_allow_html=True
    )

    for doc in active_doc_names:
        c_doc, c_act = st.columns([3.8, 1.2], gap="small")
        with c_doc:
            icon = get_media_icon(doc)
            short = doc[:18] + ("…" if len(doc) > 18 else "")
            if st.button(f"{icon} {short}", key=f"view_spec_{doc}", use_container_width=True):
                reset_viewer(doc_name=doc, open_viewer=True)
                st.rerun()

        with c_act:
            if st.button("🗑️", key=f"del_doc_{doc}", help=f"Eliminar {doc}"):
                rag_engine.delete_document(doc, uploads_dir=uploads_dir)
                notebook_mgr.remove_document_from_notebook(active_id, doc)
                st.session_state.notebook_data = notebook_mgr.load_all()
                st.rerun()
