"""
Traceability View UI — Órgano Sináptico / Telemetría y Trazabilidad de Flujo.
Monitorización del ciclo de vida en tiempo real: Ingestión, Búsqueda Vectorial e Inferencia Multimodal.
"""
import streamlit as st

from core.traceability import trace_manager


def render_traceability_view(rag_engine, stats_manager):
    """Renderiza el órgano sináptico de telemetría."""
    st.markdown('<div class="creature-organ speed-meltable">', unsafe_allow_html=True)
    _render_telemetry_kpis(stats_manager)
    st.markdown("</div>", unsafe_allow_html=True)

    tab_traces, tab_diagram = st.tabs(["📜 Impulsos y Trazas de Flujo", "🗺️ Mapa Sináptico del Pipeline"])

    with tab_traces:
        _render_traces_list()

    with tab_diagram:
        _render_flow_diagram()


def _render_telemetry_kpis(stats_manager):
    """Muestra telemetría de latencia, impulsos y salud del hardware."""
    telemetry = trace_manager.get_system_telemetry()

    c_title, c_back = st.columns([4, 1.2])
    with c_title:
        st.markdown(
            '<div style="display:flex; align-items:center; gap:8px;">'
            '<span style="font-size:1.3rem;">⚡</span>'
            '<span style="font-weight:800; font-size:1.1rem; letter-spacing:0.04em; text-transform:uppercase; color:var(--mercurio);">'
            'Órgano Sináptico // Telemetría'
            '</span>'
            '</div>'
            '<div class="whisper-text" style="font-size:0.85rem; color:var(--lima); margin-top:2px;">'
            '« Ciclo de vida RAG en tiempo real · Ingestión · Búsqueda Qdrant · Inferencia LLM »'
            '</div>',
            unsafe_allow_html=True
        )
    with c_back:
        if st.button("💬 Volver al Diálogo", key="btn_back_to_chat", use_container_width=True):
            st.session_state.show_traceability = False
            st.rerun()

    st.markdown("<hr style='border-color:rgba(207,216,218,0.15); margin:10px 0;'>", unsafe_allow_html=True)

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric(
            label="Total Trazas Registradas",
            value=f"{telemetry['total_traces']} ev",
            help="Número de flujos de consulta e indexación monitoreados"
        )
    with col2:
        st.metric(
            label="Latencia Promedio",
            value=f"{telemetry['avg_latency_ms']} ms",
            help="Tiempo medio de ejecución de las operaciones del sistema"
        )
    with col3:
        mode = st.session_state.get("llm_mode", "local")
        if mode == "cloud":
            model = st.session_state.get("cloud_model", "cloud")
            prov = st.session_state.get("cloud_provider", "groq").upper()
            st.metric(
                label="Motor de Inferencia",
                value=f"☁️ {model[:12]}",
                delta=f"API {prov}",
                help=f"Modelo en la nube {model} conectado vía {prov}"
            )
        else:
            st.metric(
                label="Visión/Chat (GPU)",
                value="qwen2.5vl:7b",
                delta="RTX 5050 · 8k ctx",
                help="Modelo multimodal sobre GPU dedicada con contexto de 8192 tokens"
            )
    with col4:
        st.metric(
            label="Vectores (CPU)",
            value="embeddinggemma-2",
            delta="num_gpu=0 Aislado",
            help="Modelo de embeddings forzado a CPU/RAM para proteger la VRAM"
        )


def _render_traces_list():
    """Renderiza el listado secuencial de trazas de ejecución."""
    c_filter, c_actions = st.columns([3, 2])
    with c_filter:
        flow_filter = st.selectbox(
            "Filtrar por tipo de flujo:",
            options=[
                ("all", "Todos los flujos"),
                ("query", "💬 Consultas RAG e Inferencia"),
                ("ingestion_video", "🎬 Ingestión de Videos"),
                ("ingestion_audio", "🎵 Ingestión de Audios"),
                ("ingestion_pdf", "📄 Ingestión de PDFs"),
                ("ingestion_image", "🖼️ Ingestión de Imágenes"),
                ("deletion", "🗑️ Eliminación y Purga"),
            ],
            format_func=lambda x: x[1],
            key="trace_flow_filter"
        )
    with c_actions:
        st.markdown("<div style='height:26px;'></div>", unsafe_allow_html=True)
        c_ref, c_clr = st.columns(2)
        with c_ref:
            if st.button("🔄 Refrescar", key="btn_refresh_traces", use_container_width=True):
                st.rerun()
        with c_clr:
            if st.button("🗑️ Limpiar", key="btn_clear_traces", use_container_width=True):
                trace_manager.clear_all_traces()
                st.toast("Trazas limpiadas.")
                st.rerun()

    traces = trace_manager.get_recent_traces(limit=40, flow_type=flow_filter[0])

    if not traces:
        st.info("No se han registrado trazas para este filtro aún.")
        return

    for t in traces:
        _render_trace_card(t)


def _render_trace_card(trace: dict):
    """Ficha individual de una traza con pasos cronológicos detallados."""
    status_icon = "🟢" if trace.get("status") == "success" else ("⏳" if trace.get("status") == "running" else "🔴")
    f_type = trace.get("flow_type", "general").upper()
    dur_str = f"{trace.get('total_duration_ms', 0):.0f} ms"
    if trace.get("total_duration_ms", 0) > 1000:
        dur_str = f"{trace.get('total_duration_ms', 0) / 1000:.2f} s"

    header_label = f"{status_icon} [{trace.get('start_time', '')}] {trace.get('title', 'Flujo')} · ⏱️ {dur_str}"

    with st.expander(header_label, expanded=(trace.get("status") == "running")):
        st.markdown(
            f"<div style='font-size:0.75rem; margin-bottom:8px; color:var(--mercurio);'>"
            f"<b>ID Traza:</b> <code>{trace.get('trace_id')}</code> | "
            f"<b>Tipo:</b> <code>{f_type}</code> | "
            f"<b>Estado:</b> <span style='color:var(--lima); font-weight:700;'>{trace.get('status', '').upper()}</span> | "
            f"<b>Resumen:</b> {trace.get('summary', 'Completado')}"
            f"</div>",
            unsafe_allow_html=True
        )

        steps = trace.get("steps", [])
        if not steps:
            st.caption("No hay pasos detallados registrados.")
            return

        st.markdown(
            "<div style='font-size:0.75rem; font-weight:800; text-transform:uppercase; letter-spacing:0.06em; color:var(--mercurio); margin-bottom:6px;'>"
            "Secuencia de impulsos del pipeline:</div>",
            unsafe_allow_html=True
        )

        for s_idx, step in enumerate(steps):
            s_status = "✅" if step.get("status") == "success" else ("⚠️" if step.get("status") == "warning" else "❌")
            s_dur = f"+{step.get('duration_ms', 0):.0f} ms" if step.get("duration_ms", 0) > 0 else ""

            col_idx, col_body = st.columns([0.4, 5.6])
            with col_idx:
                st.markdown(f"<div style='font-weight:700; color:var(--naranja); font-size:0.88rem; text-align:right;'>{s_idx + 1}.</div>", unsafe_allow_html=True)
            with col_body:
                st.markdown(
                    f"<div style='background:rgba(6,26,32,0.8); border-left:3px solid var(--lima); padding:6px 12px; border-radius:6px; margin-bottom:6px; font-size:0.78rem;'>"
                    f"{s_status} <b style='color:var(--mercurio);'>{step.get('name')}</b> <span style='float:right; opacity:0.7; color:var(--mercurio);'>{step.get('timestamp', '')} {s_dur}</span><br>"
                    f"<span class='whisper-text' style='font-size:0.82rem; color:var(--mercurio);'>{step.get('details', '')}</span>"
                    f"</div>",
                    unsafe_allow_html=True
                )
                meta = step.get("metadata", {})
                if meta:
                    with st.expander(f"Metadatos del paso {s_idx + 1}", expanded=False):
                        st.json(meta)


def _render_flow_diagram():
    """Diagrama de flujo sináptico del sistema RAG multimodal."""
    st.markdown(
        """
```mermaid
graph TD
    subgraph INGESTION ["1. Ingesta y Digestión Vectorial Multimodal"]
        A[Espécimen Subido] --> B{Tipo de Medio}
        B -->|PDF| C1[PyMuPDF: Texto + Gráficos]
        B -->|Audio| C2[Normalización WAV + Transcripción por Lapsos]
        B -->|Video| C3[Descomposición: Pista Audio + Keyframes]
        B -->|Imagen| C4[Inspección Directa]
        
        C1 & C3 & C4 --> D[Qwen2.5-VL en GPU: Comprensión Visual + Taxonomía]
        C1 & C2 & C3 & C4 --> E[EmbeddingGemma-2 en CPU: Vectorización 768d]
        
        D & E --> F[(Qdrant Vector DB: Puerto 6333)]
        D & E --> G[(SQLite: Ficha Técnica Inmutable)]
    end

    subgraph RETRIEVAL ["2. Recuperación Híbrida y Diálogo"]
        Q[Impulso del Usuario] --> H[Detección de Pliego Objetivo]
        H --> I[Qdrant: Búsqueda Vectorial Prioritaria]
        I --> J[Inyección Ficha Técnica SQLite]
        I --> K{¿Consulta Visual?}
        K -->|Sí| L[Fotograma/Imagen Optimizada a 512px]
        K -->|No| M[Solo Contexto Recuperado]
        J & L & M --> S{Motor Inferencia}
        S -->|Local| N1[Ollama: Qwen2.5-VL en GPU 8k]
        S -->|Nube| N2[API: Groq / OpenAI / Gemini]
        N1 & N2 --> O[Streaming en Tiempo Real + Citas Precisas]
    end
```
        """
    )
