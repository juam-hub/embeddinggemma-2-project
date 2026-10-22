"""Session state initialization and management for ChatCasero."""
import streamlit as st


def init_session_state(notebook_mgr):
    """Initialize all persistent session state variables.

    Returns:
        Tuple of (active_id, active_notebook, active_doc_names).
    """
    if "notebook_data" not in st.session_state:
        st.session_state.notebook_data = notebook_mgr.load_all()

    notebooks = st.session_state.notebook_data.get("notebooks", {})
    active_id = st.session_state.notebook_data.get("active_id")

    if active_id not in notebooks:
        if notebooks:
            st.session_state.notebook_data["active_id"] = list(notebooks.keys())[0]
        else:
            notebook_mgr.create_notebook("Cuaderno n.º 001")
            st.session_state.notebook_data = notebook_mgr.load_all()

    active_id = st.session_state.notebook_data["active_id"]
    active_notebook = st.session_state.notebook_data["notebooks"][active_id]
    active_doc_names = active_notebook.get("doc_names", [])

    # Viewer state defaults
    for key, default in [
        ("viewer_open", False),
        ("current_view_doc", active_doc_names[0] if active_doc_names else ""),
        ("current_view_page", 1),
        ("current_view_snippet", ""),
        ("current_view_element_id", ""),
        ("current_view_start_time", 0.0),
        ("current_view_end_time", 0.0),
        ("current_view_timestamp_label", ""),
        ("llm_mode", "local"),
        ("cloud_provider", "groq"),
        ("cloud_api_key", ""),
        ("cloud_model", "llama-3.3-70b-versatile"),
        ("cloud_custom_url", ""),
        ("cloud_conn_tested", False),
        ("cloud_conn_success", False),
        ("cloud_conn_msg", ""),
    ]:
        if key not in st.session_state:
            st.session_state[key] = default

    # Ensure current_view_doc is valid
    if active_doc_names and (
        not st.session_state.current_view_doc
        or st.session_state.current_view_doc not in active_doc_names
    ):
        st.session_state.current_view_doc = active_doc_names[0]

    return active_id, active_notebook, active_doc_names


def reset_viewer(
    doc_name="",
    page=1,
    snippet="",
    element_id="",
    open_viewer=None,
    start_time=0.0,
    end_time=0.0,
    timestamp_label=""
):
    """Update viewer state variables in one call."""
    if doc_name:
        st.session_state.current_view_doc = doc_name
    st.session_state.current_view_page = page
    st.session_state.current_view_snippet = snippet
    st.session_state.current_view_element_id = element_id
    st.session_state.current_view_start_time = float(start_time or 0.0)
    st.session_state.current_view_end_time = float(end_time or 0.0)
    st.session_state.current_view_timestamp_label = timestamp_label or ""
    if open_viewer is not None:
        st.session_state.viewer_open = open_viewer
