import streamlit as st
import requests

# =========================================================
# CONFIG
# =========================================================

BACKEND_URL = "http://127.0.0.1:8000"

st.set_page_config(
    page_title="Autonomous AI Research System",
    layout="wide"
)

# =========================================================
# SESSION STATE INIT
# =========================================================

if "uploaded_files" not in st.session_state:
    st.session_state.uploaded_files = []

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

# =========================================================
# CHECK BACKEND STATUS ON LOAD
# =========================================================

def check_upload_status():
    """Check backend for current upload status."""
    try:
        resp = requests.get(f"{BACKEND_URL}/upload/status", timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            st.session_state.uploaded_files = data.get("uploaded_files", [])
            return data.get("retriever_ready", False)
    except Exception:
        pass
    return False

retriever_ready = check_upload_status()

# =========================================================
# TITLE
# =========================================================

st.title("🧠 Autonomous AI Research System")

# =========================================================
# SIDEBAR
# =========================================================

st.sidebar.title("⚙️ Settings")

show_sources = st.sidebar.toggle(
    "Show Sources",
    value=True
)

st.sidebar.markdown("---")

# =========================================================
# UPLOAD STATUS
# =========================================================

st.sidebar.header("📂 Upload Status")

if retriever_ready:
    st.sidebar.success(f"✅ Retriever ready ({len(st.session_state.uploaded_files)} file(s))")
else:
    st.sidebar.warning("⚠️ No documents uploaded yet")

if st.session_state.uploaded_files:
    with st.sidebar.expander("📄 Uploaded Files"):
        for f in st.session_state.uploaded_files:
            st.text(f"• {f}")

st.sidebar.markdown("---")

# =========================================================
# FILE UPLOAD (Multi-file support)
# =========================================================

st.sidebar.header("📂 Upload Documents")

uploaded_files = st.sidebar.file_uploader(
    "Upload PDFs or TXT",
    type=["pdf", "txt"],
    accept_multiple_files=True
)

# =========================================================
# UPLOAD BUTTON
# =========================================================

if st.sidebar.button("🚀 Upload Files"):

    if not uploaded_files:

        st.sidebar.error("Please select files first")

    else:

        success_count = 0
        error_count = 0

        progress_bar = st.sidebar.progress(0)
        status_text = st.sidebar.empty()

        for i, uploaded_file in enumerate(uploaded_files):

            try:

                status_text.text(f"📤 Uploading {uploaded_file.name}...")

                files = {
                    "file": (
                        uploaded_file.name,
                        uploaded_file.getvalue(),
                        uploaded_file.type
                    )
                }

                response = requests.post(
                    f"{BACKEND_URL}/upload",
                    files=files,
                    timeout=300
                )

                if response.status_code == 200:
                    success_count += 1
                    if uploaded_file.name not in st.session_state.uploaded_files:
                        st.session_state.uploaded_files.append(uploaded_file.name)
                else:
                    error_count += 1

            except Exception as e:
                error_count += 1
                st.sidebar.error(f"❌ {uploaded_file.name}: {str(e)}")

            progress_bar.progress((i + 1) / len(uploaded_files))

        status_text.text("")

        if success_count > 0:
            st.sidebar.success(f"✅ {success_count} file(s) uploaded successfully")
            # Refresh status
            retriever_ready = check_upload_status()

        if error_count > 0:
            st.sidebar.error(f"❌ {error_count} file(s) failed")

# =========================================================
# MEMORY PANEL
# =========================================================

st.sidebar.markdown("---")
st.sidebar.header("🧠 Memory")

with st.sidebar.expander("View Memory Contents"):
    try:
        mem_resp = requests.get(f"{BACKEND_URL}/memory/default_session", timeout=5)
        if mem_resp.status_code == 200:
            mem_data = mem_resp.json()
            
            st.subheader("Short-Term Memory")
            st.caption(f"Count: {mem_data.get('short_term_count', 0)}")
            for item in mem_data.get("short_term", []):
                with st.container():
                    st.markdown(f"**Q:** {item.get('query', '')[:80]}")
                    st.markdown(f"**A:** {item.get('answer', '')[:100]}...")
                    st.divider()
            
            st.subheader("Long-Term Memory (SQLite)")
            st.caption(f"Count: {mem_data.get('long_term_count', 0)}")
            for item in mem_data.get("long_term", []):
                with st.container():
                    st.markdown(f"**Q:** {item.get('query', '')[:80]}")
                    st.markdown(f"**A:** {item.get('answer', '')[:100]}...")
                    st.caption(f"Confidence: {item.get('confidence', 'N/A')}% | {item.get('timestamp', '')}")
                    st.divider()
        else:
            st.info("No memory data available")
    except Exception as e:
        st.info(f"Could not load memory: {e}")

if st.sidebar.button("🗑️ Clear Memory"):
    try:
        resp = requests.delete(f"{BACKEND_URL}/memory/default_session", timeout=5)
        if resp.status_code == 200:
            st.sidebar.success("Memory cleared!")
            st.rerun()
    except Exception as e:
        st.sidebar.error(f"Failed to clear: {e}")

# =========================================================
# CHAT HISTORY
# =========================================================

for chat in st.session_state.chat_history:
    with st.chat_message(chat["role"]):
        st.markdown(chat["content"])

# =========================================================
# QUERY INPUT
# =========================================================

query = st.chat_input(
    "Ask a question..."
)

# =========================================================
# QUERY
# =========================================================

if query:

    st.chat_message("user").markdown(query)

    with st.spinner("🧠 Running AI pipeline..."):

        try:

            response = requests.post(
                f"{BACKEND_URL}/query",
                params={"q": query},
                timeout=300
            )

            data = response.json()

            answer = data.get("answer", "")
            citations = data.get("citations", [])

            with st.chat_message("assistant"):

                # Show only the answer text
                st.markdown(answer)

                # Show citations if toggle is on
                if show_sources and citations:
                    st.markdown("---")
                    st.markdown("📚 **Sources**")
                    for i, cit in enumerate(citations):
                        file_name = cit.get("file_name", "Unknown")
                        text_snippet = cit.get("text_snippet", "")
                        score = cit.get("score", None)
                        
                        with st.container():
                            st.markdown(f"**Source {i+1}:** `{file_name}`")
                            if score is not None:
                                st.caption(f"Relevance: {score}")
                            st.markdown(f"> {text_snippet}")
                            st.divider()

            # Store in chat history
            st.session_state.chat_history.append({"role": "user", "content": query})
            st.session_state.chat_history.append({"role": "assistant", "content": answer})

        except Exception as e:

            st.error(str(e))