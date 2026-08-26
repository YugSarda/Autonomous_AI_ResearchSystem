import streamlit as st
import requests
import time
import uuid

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

# Generate a unique session ID per browser session for user isolation
if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())

if "uploaded_files" not in st.session_state:
    st.session_state.uploaded_files = []

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

if "active_tasks" not in st.session_state:
    st.session_state.active_tasks = {}

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
            
            # Check for active tasks
            recent_tasks = data.get("recent_tasks", [])
            for task in recent_tasks:
                if task["status"] in ("pending", "processing"):
                    st.session_state.active_tasks[task["task_id"]] = task
            
            return data.get("retriever_ready", False)
    except Exception:
        pass
    return False

retriever_ready = check_upload_status()

# =========================================================
# POLL ASYNC TASKS
# =========================================================

def poll_async_tasks():
    """Poll backend for status of active async tasks."""
    completed_tasks = []
    for task_id, task_info in st.session_state.active_tasks.items():
        try:
            resp = requests.get(f"{BACKEND_URL}/upload/status/{task_id}", timeout=5)
            if resp.status_code == 200:
                task_data = resp.json()
                if task_data["status"] in ("done", "failed"):
                    completed_tasks.append(task_id)
                    st.session_state.active_tasks[task_id] = task_data
        except Exception:
            pass
    
    # Remove completed tasks from active tracking
    for task_id in completed_tasks:
        if task_id in st.session_state.active_tasks:
            task = st.session_state.active_tasks[task_id]
            if task["status"] == "done":
                st.success(f"✅ Async ingestion complete: {task['filename']}")
            elif task["status"] == "failed":
                st.error(f"❌ Async ingestion failed: {task['filename']} - {task.get('message', '')}")
            # Keep in session state for display but mark as no longer "active"
    
    # Refresh retriever status
    if completed_tasks:
        check_upload_status()

# Poll async tasks every time the app runs
if st.session_state.active_tasks:
    poll_async_tasks()

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

# =========================================================
# PENDING ASYNC TASKS
# =========================================================

if st.session_state.active_tasks:
    with st.sidebar.expander("⏳ Active Ingestion Tasks", expanded=True):
        for task_id, task in list(st.session_state.active_tasks.items()):
            status = task.get("status", "unknown")
            filename = task.get("filename", "Unknown")
            
            if status == "pending":
                st.markdown(f"⏳ **{filename}**: Queued...")
            elif status == "processing":
                st.markdown(f"🔄 **{filename}**: Processing...")
                st.progress(0.5, text="")
            elif status == "done":
                st.markdown(f"✅ **{filename}**: Complete")
            elif status == "failed":
                st.markdown(f"❌ **{filename}**: Failed - {task.get('message', '')}")

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
        async_count = 0

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
                    data = response.json()
                    
                    # Check if async ingestion was started
                    if data.get("async"):
                        async_count += 1
                        task_id = data.get("task_id")
                        if task_id:
                            st.session_state.active_tasks[task_id] = {
                                "task_id": task_id,
                                "filename": uploaded_file.name,
                                "status": "pending"
                            }
                        st.sidebar.info(f"⏳ {uploaded_file.name}: Async ingestion queued")
                    else:
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
            st.sidebar.success(f"✅ {success_count} file(s) uploaded and indexed")
            # Refresh status
            retriever_ready = check_upload_status()

        if async_count > 0:
            st.sidebar.info(f"⏳ {async_count} file(s) queued for async ingestion")

        if error_count > 0:
            st.sidebar.error(f"❌ {error_count} file(s) failed")

# =========================================================
# MEMORY PANEL
# =========================================================

st.sidebar.markdown("---")
st.sidebar.header("🧠 Memory")

with st.sidebar.expander("View Memory Contents"):
    try:
        mem_resp = requests.get(f"{BACKEND_URL}/memory/{st.session_state.session_id}", timeout=5)
        if mem_resp.status_code == 200:
            mem_data = mem_resp.json()
            
            st.subheader("Short-Term Memory")
            st.caption(f"Count: {mem_data.get('short_term_count', 0)}")
            for item in mem_data.get("short_term", []):
                with st.container():
                    st.markdown(f"**Q:** {item.get('query', '')[:80]}")
                    st.markdown(f"**A:** {item.get('answer', '')[:100]}...")
                    st.divider()
            
            st.subheader("Long-Term Memory (PostgreSQL)")
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
        resp = requests.delete(f"{BACKEND_URL}/memory/{st.session_state.session_id}", timeout=5)
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
                params={"q": query, "session_id": st.session_state.session_id},
                timeout=300,
                headers={"X-Session-ID": st.session_state.session_id}
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