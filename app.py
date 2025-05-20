# File: app.py

import streamlit as st
import uuid
from backend.file_handler import extract_text_from_files
from backend.embedder import embed_and_store, load_vectorstore
from backend.chat_engine import ask_question
from backend.logger import log_chat, log_uploaded_files

# Set up the Streamlit web app with wide layout and title
st.set_page_config(page_title="AI Tutor MVP", layout="wide")
st.title("📚 AI Tutor MVP")

# Generate a unique session ID for each user session
session_id = str(uuid.uuid4())

# Let user upload multiple file types at once
uploaded_files = st.file_uploader(
    "Upload PDF, TXT, or Image files",
    type=["pdf", "txt", "png", "jpg", "jpeg"],
    accept_multiple_files=True
)

if uploaded_files:
    with st.spinner("Extracting content..."):
        # Extract and clean text from all uploaded files
        raw_text, filenames = extract_text_from_files(uploaded_files)
        # Store vectorized content linked to this session
        embed_and_store(raw_text, session_id)
        # Log the names of uploaded files for tracking
        log_uploaded_files(session_id, filenames)
        st.success("Content processed and indexed.")

    st.subheader("Ask Your Tutor")
    user_query = st.text_input("Type a question:", key="question")

    if user_query:
        # Run user question through context-aware tutor model
        response = ask_question(user_query, session_id)
        st.write(response)
        # Save each Q&A to logs for future review or training
        log_chat(session_id, user_query, response)
