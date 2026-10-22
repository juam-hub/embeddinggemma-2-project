"""
Chat UI — Órgano Neural / Diálogo Multimodal de la Criatura Líquida.
Conversación con masa e inercia, citas líquidas con salto temporal y folios, y zona tranquila de entrada.
"""
import streamlit as st
from ui.state import reset_viewer


def render_chat(rag_engine, notebook_mgr, active_id, active_notebook, active_doc_names):
    """Renderiza el órgano de diálogo neural: contenedor con scroll, burbujas y zona tranquila."""
    st.markdown('<div class="creature-organ speed-meltable">', unsafe_allow_html=True)
    
    # Encabezado del Órgano
    st.markdown(
        '<div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:12px; border-bottom:1px solid rgba(207,216,218,0.12); padding-bottom:8px;">'
        '<div style="display:flex; align-items:center; gap:8px;">'
        '<span style="font-size:1.2rem;">🧠</span>'
        '<span style="font-weight:800; font-size:0.92rem; letter-spacing:0.04em; text-transform:uppercase; color:var(--mercurio);">'
        'Órgano Neural // Diálogo'
        '</span>'
        '</div>'
        '<span class="whisper-text" style="font-size:0.85rem; color:var(--lima);">'
        'frecuencia sináptica estable'
        '</span>'
        '</div>',
        unsafe_allow_html=True
    )

    if not active_doc_names:
        _render_empty_state(active_notebook)
        st.markdown('</div>', unsafe_allow_html=True)
        return

    # Contenedor con scroll interno para los mensajes
    chat_box = st.container(height=560, border=False)

    with chat_box:
        _render_history(active_notebook, active_id)

    # Chat input en Zona Tranquila (Quiet Zone)
    user_query = st.chat_input(
        f"Transmitir impulso a la criatura sobre los {len(active_doc_names)} especímenes…"
    )
    if user_query:
        _handle_query(
            user_query, chat_box, rag_engine, notebook_mgr,
            active_id, active_notebook, active_doc_names,
        )

    st.markdown('</div>', unsafe_allow_html=True)


def _render_empty_state(active_notebook):
    """Estado vacío: organismo en latencia esperando especímenes."""
    st.markdown(
        f'<div style="padding: 1.8rem 1.4rem; text-align: center; border: 1.5px dashed rgba(207,216,218,0.2); border-radius: 20px; background: rgba(6,26,32,0.6);">'
        f'<div style="font-size: 2.2rem; margin-bottom: 8px;">🧪</div>'
        f'<div class="organ-badge active-orange" style="margin-bottom: 12px;">ESTADO: ORGANISMO EN LATENCIA</div>'
        f'<h3 style="font-size: 1.6rem; color: var(--mercurio); margin-bottom: 8px;">'
        f'Alimenta a la criatura para despertar la sinapsis</h3>'
        f'<p class="whisper-text" style="font-size: 1.05rem; max-width: 520px; margin: 0 auto 16px; line-height: 1.5;">'
        f'« Ingiere documentos PDF, grabaciones sonoras, videos u hojas de datos en el vientre del panel lateral. '
        f'La criatura descompondrá cada fotograma, onda de audio y fragmento semántico en el espacio vectorial. »'
        f'</p>'
        f'<div style="display:inline-block; background:rgba(255,91,20,0.12); border:1px solid var(--naranja); border-radius:8px; padding:6px 14px; font-size:0.8rem; font-weight:700; color:var(--mercurio);">'
        f'👉 Despliega el vientre lateral para absorber especímenes multimedia'
        f'</div>'
        f'</div>',
        unsafe_allow_html=True
    )


def _render_history(active_notebook, active_id):
    """Renderiza el historial de mensajes con burbujas viscosas y citas interactivas."""
    for msg_idx, msg in enumerate(active_notebook.get("messages", [])):
        role = msg["role"]
        with st.chat_message(role):
            if role == "user":
                st.markdown(
                    f'<div class="chat-bubble-user">{msg["content"]}</div>',
                    unsafe_allow_html=True,
                )
            else:
                mode_tag = ""
                if msg.get("llm_mode") == "cloud":
                    model_name = msg.get("model", "nube")
                    mode_tag = (
                        f'<div class="whisper-text" style="font-size:0.75rem; color:var(--naranja); margin-bottom:6px;">'
                        f'☁️ Inferencia en la Nube ({model_name})</div>'
                    )
                elif msg.get("llm_mode") == "local":
                    mode_tag = (
                        '<div class="whisper-text" style="font-size:0.75rem; color:var(--lima); margin-bottom:6px;">'
                        '🖥️ Inferencia Local GPU (Qwen2.5-VL · 8k ctx)</div>'
                    )

                st.markdown(
                    f'<div class="chat-bubble-assistant">'
                    f'{mode_tag}'
                    f'<div style="color:var(--mercurio); line-height:1.65;">{msg["content"]}</div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )
                _render_citations(
                    msg.get("citations", []),
                    key_prefix=f"cit_{active_id}_{msg_idx}",
                )


def _render_citations(citations, key_prefix):
    """Renderiza botones de citas líquidas con intervalo temporal o folios de página."""
    if not citations:
        return

    st.markdown(
        '<div style="font-size:0.72rem; font-weight:800; letter-spacing:0.08em; text-transform:uppercase; color:var(--mercurio); opacity:0.7; margin: 8px 0 4px 4px;">'
        '⚡ Destellos de Evidencia (Clic para enfocar en el Ojo):'
        '</div>',
        unsafe_allow_html=True,
    )

    cols = st.columns(min(3, len(citations)))
    for idx, cit in enumerate(citations):
        with cols[idx % len(cols)]:
            is_vis = cit.get("source_type") == "visual" or bool(cit.get("element_id"))
            m_type = cit.get("media_type") or "pdf"
            t_lbl = cit.get("timestamp_label", "")

            if m_type == "audio" or "audio" in cit.get("source_type", ""):
                icon = "🎵"
                loc_label = f"⏱️ {t_lbl}" if t_lbl else "Audio"
            elif m_type == "video":
                icon = "🎬"
                cat = f" [{cit.get('visual_category', 'Video')[:6]}]" if is_vis else ""
                loc_label = f"⏱️ {t_lbl}{cat}" if t_lbl else f"p.{cit['page_number']}"
            elif is_vis:
                icon = "🖼️"
                cat = f" [{cit.get('visual_category', 'Img')[:6]}]"
                loc_label = f"p.{cit['page_number']}{cat}"
            else:
                icon = "📄"
                loc_label = f"p.{cit['page_number']}"

            doc_short = cit["doc_name"][:14] + ("…" if len(cit["doc_name"]) > 14 else "")
            label = f"{icon} {loc_label} · {doc_short}"

            if st.button(label, key=f"{key_prefix}_{idx}",
                         help=f"Enfocar cita de {cit['doc_name']} ({loc_label})"):
                reset_viewer(
                    doc_name=cit["doc_name"],
                    page=cit["page_number"],
                    snippet=cit.get("snippet", ""),
                    element_id=cit.get("element_id", ""),
                    start_time=cit.get("start_time", 0.0),
                    end_time=cit.get("end_time", 0.0),
                    timestamp_label=cit.get("timestamp_label", ""),
                    open_viewer=True,
                )
                st.rerun()


def _handle_query(user_query, chat_box, rag_engine, notebook_mgr,
                  active_id, active_notebook, active_doc_names):
    """Procesa el impulso de consulta: streaming en vivo, persistencia y auto-enfoque."""
    with chat_box:
        st.chat_message("user").markdown(
            f'<div class="chat-bubble-user">{user_query}</div>',
            unsafe_allow_html=True,
        )

    active_notebook["messages"].append({
        "role": "user", "content": user_query
    })

    # Renombrar automáticamente cuaderno en el primer mensaje
    title = active_notebook["title"]
    if title.startswith("Cuaderno n.º") or title == "Cuaderno Principal":
        new_title = user_query[:28] + ("…" if len(user_query) > 28 else "")
        active_notebook["title"] = new_title
        notebook_mgr.update_notebook(active_id, {"title": new_title})

    llm_mode = st.session_state.get("llm_mode", "local")
    cloud_config = {
        "provider": st.session_state.get("cloud_provider", "groq"),
        "api_key": st.session_state.get("cloud_api_key", ""),
        "model": st.session_state.get("cloud_model", ""),
        "custom_url": st.session_state.get("cloud_custom_url", ""),
    }

    with chat_box:
        with st.chat_message("assistant"):
            if llm_mode == "cloud":
                spinner_msg = f"Invocando sinapsis en la nube ({cloud_config['provider'].upper()} · {cloud_config['model']})…"
            else:
                spinner_msg = "La criatura sintetiza evidencias multimodales (GPU Qwen2.5-VL)…"

            with st.spinner(spinner_msg):
                stream_gen, citations = rag_engine.query(
                    doc_names=active_doc_names,
                    user_query=user_query,
                    chat_history=active_notebook["messages"][:-1],
                    llm_mode=llm_mode,
                    cloud_config=cloud_config,
                )

            response_text = st.write_stream(stream_gen)

            _render_citations(
                citations,
                key_prefix=f"new_cit_{active_id}",
            )

    active_notebook["messages"].append({
        "role": "assistant",
        "content": response_text,
        "citations": citations,
        "llm_mode": llm_mode,
        "model": cloud_config["model"] if llm_mode == "cloud" else "qwen2.5vl:7b",
    })
    notebook_mgr.update_notebook(
        active_id, {"messages": active_notebook["messages"]}
    )
    st.session_state.notebook_data = notebook_mgr.load_all()

    # Enfocar automáticamente en el visor si está abierto
    if citations and st.session_state.get("viewer_open", False):
        top = citations[0]
        reset_viewer(
            doc_name=top["doc_name"],
            page=top["page_number"],
            snippet=top.get("snippet", ""),
            element_id=top.get("element_id", ""),
            start_time=top.get("start_time", 0.0),
            end_time=top.get("end_time", 0.0),
            timestamp_label=top.get("timestamp_label", ""),
        )
