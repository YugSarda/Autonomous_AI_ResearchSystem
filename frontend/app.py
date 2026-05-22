# import streamlit as st
# import requests
# import asyncio
# import aiohttp
# import base64
# from io import BytesIO
# from reportlab.pdfgen import canvas

# # ================= CONFIG =================
# BACKEND_URL = "http://localhost:8000"

# st.set_page_config(page_title="Autonomous AI Research System", layout="wide")

# # ================= SESSION STATE =================
# if "chat_history" not in st.session_state:
#     st.session_state.chat_history = []

# if "debug" not in st.session_state:
#     st.session_state.debug = {}

# # ================= SIDEBAR =================
# st.sidebar.title("⚙️ Settings")

# show_reasoning = st.sidebar.toggle("Show Reasoning", value=True)
# show_sources = st.sidebar.toggle("Show Sources", value=True)

# st.sidebar.markdown("---")
# st.sidebar.header("📂 Upload Documents")

# uploaded_files = st.sidebar.file_uploader(
#     "Upload PDFs or TXT",
#     type=["pdf", "txt"],
#     accept_multiple_files=True
# )

# if uploaded_files:
#     for file in uploaded_files:
#         files = {"file": (file.name, file.getvalue())}
#         requests.post(f"{BACKEND_URL}/upload", files=files)
#     st.sidebar.success("Files uploaded successfully!")

# # ================= MAIN TITLE =================
# st.title("🧠 Autonomous AI Research System")

# # ================= CHAT DISPLAY =================
# for chat in st.session_state.chat_history:
#     with st.chat_message(chat["role"]):
#         st.markdown(chat["content"])

# # ================= QUERY INPUT =================
# query = st.chat_input("Ask a research question...")

# # ================= STREAM FUNCTION =================
# async def stream_response(query):
#     async with aiohttp.ClientSession() as session:
#         async with session.post(f"{BACKEND_URL}/query/stream?q={query}") as resp:
#             async for chunk in resp.content:
#                 yield chunk.decode("utf-8")

# # ================= PDF DOWNLOAD =================
# def generate_pdf(text):
#     buffer = BytesIO()
#     c = canvas.Canvas(buffer)
#     c.drawString(50, 800, text[:1000])
#     c.save()
#     buffer.seek(0)
#     return buffer

# # ================= MAIN LOGIC =================
# if query:
#     st.session_state.chat_history.append({"role": "user", "content": query})

#     with st.chat_message("user"):
#         st.markdown(query)

#     with st.chat_message("assistant"):

#         response_placeholder = st.empty()
#         full_response = {"text": ""}

# async def display_stream():
#     async for chunk in stream_response(query):
#         full_response["text"] += chunk
#         response_placeholder.markdown(full_response["text"])

#         asyncio.run(display_stream())

#         # FINAL RESPONSE (FOR METADATA)
#         api_response = requests.post(
#             f"{BACKEND_URL}/query",
#             params={"q": query}
#         ).json()

#         answer = api_response.get("answer", "")
#         confidence = api_response.get("confidence", 0)
#         sources = api_response.get("sources", [])
#         logs = api_response.get("logs", [])
#         metrics = api_response.get("metrics", {})

#         # ================= DISPLAY OUTPUT =================

#         st.markdown("### 📊 Confidence Score")
#         st.progress(confidence / 100)
#         st.write(f"**{confidence}% Confidence**")

#         if show_sources:
#             st.markdown("### 📚 Sources")
#             for src in sources[:5]:
#                 st.code(str(src))

#         if show_reasoning:
#             st.markdown("### 🧠 Agent Reasoning")
#             for log in logs:
#                 st.text(log)

#         # ================= DEBUG PANEL =================
#         with st.expander("🔍 Debug Panel"):

#             st.subheader("⚙️ Metrics")
#             st.json(metrics)

#             st.subheader("📜 Raw Logs")
#             st.write(logs)

#         # ================= DOWNLOAD =================
#         pdf_buffer = generate_pdf(answer)
#         st.download_button(
#             label="📄 Download Answer as PDF",
#             data=pdf_buffer,
#             file_name="answer.pdf",
#             mime="application/pdf"
#         )

#     st.session_state.chat_history.append({"role": "assistant", "content": answer})

import streamlit as st
import requests

# =========================================================
# CONFIG
# =========================================================

BACKEND_URL = "http://127.0.0.1:8003"

st.set_page_config(
    page_title="Autonomous AI Research System",
    layout="wide"
)

# =========================================================
# TITLE
# =========================================================

st.title("🧠 Autonomous AI Research System")

# =========================================================
# SIDEBAR
# =========================================================

st.sidebar.title("⚙️ Settings")

show_reasoning = st.sidebar.toggle(
    "Show Reasoning",
    value=True
)

show_sources = st.sidebar.toggle(
    "Show Sources",
    value=True
)

st.sidebar.markdown("---")

# =========================================================
# FILE UPLOAD
# =========================================================

st.sidebar.header("📂 Upload Documents")

uploaded_file = st.sidebar.file_uploader(
    "Upload PDF or TXT",
    type=["pdf", "txt"]
)

# =========================================================
# MANUAL BUTTON
# =========================================================

if st.sidebar.button("🚀 Upload File"):

    if uploaded_file is None:

        st.sidebar.error("Please select file first")

    else:

        try:

            st.sidebar.write("📤 Sending request...")

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

            st.sidebar.success("✅ Upload successful")

            st.sidebar.json(response.json())

        except Exception as e:

            st.sidebar.error(str(e))

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

            confidence = data.get("confidence", 0)

            logs = data.get("logs", [])

            sources = data.get("sources", [])

            with st.chat_message("assistant"):

                st.markdown(answer)

                st.markdown("## 📊 Confidence")

                st.progress(confidence / 100)

                st.write(f"{confidence}%")

                if show_sources:

                    st.markdown("## 📚 Sources")

                    for src in sources[:5]:

                        st.code(str(src))

                if show_reasoning:

                    st.markdown("## 🧠 Logs")

                    for log in logs:

                        st.text(log)

        except Exception as e:

            st.error(str(e))