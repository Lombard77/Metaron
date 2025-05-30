import streamlit as st
from backend.file_handler import process_file
from backend.embedder import embed_and_store
from backend.logger import save_kb_metadata, get_kb_metadata, log_chat
from backend.chat_engine import ask_question
from backend.logger import log_uploaded_files
from backend.embedder import load_model
import os

# App Configuration
st.set_page_config(page_title="Metatron Tutor", layout="wide")

# CSS Styling
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600&display=swap');

body {
    font-family: 'Inter', sans-serif;
    background-color: #f9f9f9;
}

.custom-card {
    background: white;
    padding: 1.5rem;
    border-radius: 16px;
    box-shadow: 0 8px 30px rgba(0, 0, 0, 0.06);
    text-align: left;
    max-width: 440px;
    margin: 5vh auto;
    font-family: 'Inter', sans-serif;
    animation: fadeInUp 0.4s ease-out;
}

.custom-card h2 {
    font-size: 1.3rem;
    margin-bottom: 1rem;
}

.custom-card h3 {
    font-size: 1rem;
    margin-top: 0.5rem;
}

.custom-card input, .custom-card select, .custom-card button {
    width: 100%;
    padding: 0.45rem 0.75rem;
    font-size: 0.9rem;
    border-radius: 8px;
    border: 1px solid #ccc;
    margin-top: 0.5rem;
    margin-bottom: 0.5rem;
}

.custom-card button {
    background-color: #f1f1f1;
    font-weight: 600;
    transition: background-color 0.2s ease-in-out;
}

.custom-card button:hover {
    background-color: #e0e0e0;
}

@keyframes fadeInUp {
    from {
        opacity: 0;
        transform: translateY(20px);
    }
    to {
        opacity: 1;
        transform: translateY(0);
    }
}

.chat-bubble {
    padding: 1rem;
    border-radius: 8px;
    margin: 1rem 0;
}
.chat-user {
    background-color: #e0f7fa;
    text-align: right;
}
.chat-ai {
    background-color: #eceff1;
}
.main, .block-container {
    padding-top: 0 !important;
}
</style>
""", unsafe_allow_html=True)

# Session Init
if "user_id" not in st.session_state:
    st.session_state.user_id = None
if "active_kb" not in st.session_state:
    st.session_state.active_kb = None
if "mode" not in st.session_state:
    st.session_state.mode = "chat"
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "provider" not in st.session_state:
    st.session_state.provider = "Open Source"
if "api_key" not in st.session_state:
    st.session_state.api_key = ""
if "model_name" not in st.session_state:
    st.session_state.model_name = "mistral-7b-instruct"

# Login screen
import backend.auth as auth
auth.init_db()

if not st.session_state.get("user_id"):
    with st.container():
        st.markdown("<div class='custom-card'>", unsafe_allow_html=True)
        st.markdown("<h2>👋 Welcome to Metatron Tutor</h2>", unsafe_allow_html=True)

        is_new = st.toggle("I'm new here (sign up)", value=False)

        if is_new:
            st.markdown("### Create Your Account")
            first_name = st.text_input("First Name")
            last_name = st.text_input("Last Name")
            age_group = st.selectbox("Age Group", ["Under 12", "13–18", "19–25", "26–40", "41+"])
            email = st.text_input("Email", key="signup_email")
            password = st.text_input("Password", type="password", key="signup_password")
            if st.button("📝 Register") and all([first_name, last_name, age_group, email, password]):
                if auth.user_exists(email):
                    st.error("That email is already registered.")
                else:
                    auth.create_user(email, password, first_name, last_name, age_group)
                    st.session_state.user_id = auth.get_user_id(email)
                    st.success("✅ Registered and logged in!")
                    st.rerun()

        else:
            st.markdown("### Log In")
            email = st.text_input("Email", key="login_email")
            password = st.text_input("Password", type="password", key="login_password")
            if st.button("🔐 Log In") and email and password:
                if auth.user_exists(email):
                    if auth.validate_login(email, password):
                        st.session_state.user_id = auth.get_user_id(email)
                        st.success("✅ Login successful!")
                        st.rerun()
                    else:
                        st.error("❌ Incorrect password.")
                else:
                    st.warning("⚠️ Email not registered.")

        st.markdown("</div>", unsafe_allow_html=True)
        st.stop()

# ---- Main App ----
if st.session_state.get("user_id"):
    with st.sidebar:
        st.markdown("## 📚 Metatron Tutor")
        st.markdown(f"👤 Logged in as: `{st.session_state.user_id}`")
        st.markdown("### 📘 Study Plans")
        if st.button("➕ Add New Plan"):
            st.session_state.mode = "upload"
            st.rerun()

        kb_path = os.path.join("data", "vector_store", st.session_state.user_id)
        if os.path.exists(kb_path):
            plans = [f for f in os.listdir(kb_path) if os.path.isdir(os.path.join(kb_path, f))]
            for plan in plans:
                if st.button(f"📄 {plan}"):
                    st.session_state.active_kb = plan
                    st.session_state.mode = "chat"
                    st.rerun()

    if st.session_state.mode == "upload":
        st.markdown("## 📤 Upload Content & Create Study Plan")
        st.markdown("### 🧠 Select AI Engine")
        provider = st.radio("Choose your model", ["Open Source", "OpenAI"], key="plan_model_provider")
        st.session_state.provider = provider

        if provider == "OpenAI":
            st.session_state.model_name = st.selectbox("Model", ["gpt-3.5-turbo", "gpt-4o"], key="plan_openai_model")
            st.session_state.api_key = st.text_input("Enter OpenAI API key", type="password", key="plan_openai_key")
        else:
            st.session_state.model_name = st.selectbox("Model", ["mistral-7b-instruct", "zephyr-7b-alpha"], key="plan_hf_model")
            st.session_state.api_key = None

        uploaded_files = st.file_uploader("Upload PDF, TXT, PNG, JPG", type=["pdf", "txt", "png", "jpg", "jpeg"], accept_multiple_files=True)

        if st.session_state.provider == "OpenAI" and not st.session_state.api_key:
            st.warning("Please enter your OpenAI API key before uploading.")
            st.stop()

        if uploaded_files:
            raw_text = ""
            filenames = []
            for f in uploaded_files:
                text, name = process_file(f)
                raw_text += text + "\n"
                filenames.append(name)
            log_uploaded_files(st.session_state.user_id, filenames)

            plan_name = st.text_input("Plan name")
            intent = st.selectbox("Learning Focus", ["Study", "Revise", "Test"])
            timeframe = st.selectbox("Timeframe Type", ["7 days", "14 days", "30 days", "Custom"])
            goal = st.text_area("Goal description")

            if st.button("🚀 Create Study Plan"):
                namespace = f"{st.session_state.user_id}_{plan_name}"
                embed_and_store(raw_text, namespace, st.session_state.provider, st.session_state.api_key)
                save_kb_metadata(st.session_state.user_id, plan_name, intent, goal, timeframe)
                st.session_state.active_kb = plan_name
                st.session_state.mode = "chat"
                st.success("Study Plan created!")
                st.rerun()

    elif st.session_state.mode == "chat":
        st.markdown("## 💬 Your Metatron Study Coach")
        if not st.session_state.active_kb:
            st.info("👋 You haven’t created any study plans yet. Use the sidebar to create one.")
            st.stop()

        namespace = f"{st.session_state.user_id}_{st.session_state.active_kb}"
        question = st.text_input("Ask a question...")
        if st.button("🔍 Ask"):
            response = ask_question(question, namespace, st.session_state.api_key, st.session_state.model_name, st.session_state.provider, st.session_state.active_kb)
            st.session_state.chat_history.append(("user", question))
            st.session_state.chat_history.append(("ai", response))
            log_chat(st.session_state.user_id, st.session_state.active_kb, question, response)

        for speaker, text in st.session_state.chat_history:
            bubble_class = "chat-user" if speaker == "user" else "chat-ai"
            st.markdown(f"<div class='chat-bubble {bubble_class}'>{text}</div>", unsafe_allow_html=True)

    elif st.session_state.mode == "dashboard":
        st.markdown("## 📊 Your Learning Dashboard")
        st.markdown(f"### Plan: `{st.session_state.active_kb}`")
        meta = get_kb_metadata(st.session_state.user_id, st.session_state.active_kb)
        st.write("🧠 Intent:", meta.get("intent"))
        st.write("🎯 Goal:", meta.get("goal"))
        st.write("📅 Timeframe:", meta.get("timeframe"))
        st.write("💬 Questions asked:", len(st.session_state.chat_history))
