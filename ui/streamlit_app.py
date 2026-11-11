"""Simple chat UI that talks to the FastAPI backend.

Run:  streamlit run ui/streamlit_app.py
"""

import os

import requests
import streamlit as st

API_URL = os.getenv("API_URL", "http://localhost:8000")

st.set_page_config(page_title="DocuMind", page_icon="📚")
st.title("📚 DocuMind")
st.caption("Ask questions about your company documents. Every answer cites its sources.")

with st.sidebar:
    st.header("Knowledge base")
    try:
        st.write(requests.get(f"{API_URL}/documents", timeout=5).json())
    except requests.RequestException:
        st.error(f"API is not reachable at {API_URL}")
    uploaded = st.file_uploader("Add a document", type=["md", "txt", "pdf"])
    if uploaded and st.button("Upload & re-index"):
        r = requests.post(
            f"{API_URL}/documents", files={"file": (uploaded.name, uploaded.getvalue())}
        )
        st.success(r.json()) if r.ok else st.error(r.text)

if "history" not in st.session_state:
    st.session_state.history = []

for msg in st.session_state.history:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

if question := st.chat_input("e.g. How many vacation days do I get?"):
    st.session_state.history.append({"role": "user", "content": question})
    with st.chat_message("user"):
        st.markdown(question)

    with st.chat_message("assistant"):
        with st.spinner("Searching documents…"):
            r = requests.post(f"{API_URL}/ask", json={"question": question}, timeout=120)
        if not r.ok:
            content = f"⚠️ {r.json().get('detail', r.text)}"
        else:
            data = r.json()
            content = data["answer"]
            if data["citations"]:
                content += "\n\n**Sources:**\n" + "\n".join(
                    f"{i}. `{c['source']}` › {c['section']} — _“{c['quote']}”_"
                    for i, c in enumerate(data["citations"], 1)
                )
        st.markdown(content)
    st.session_state.history.append({"role": "assistant", "content": content})
