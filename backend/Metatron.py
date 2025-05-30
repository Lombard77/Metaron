# File: backend/chat_engine.py

import os
from embedder import load_vectorstore
from langchain.chains import RetrievalQA
from langchain_community.chat_models import ChatOpenAI  # OpenAI wrapper
from dotenv import load_dotenv
from logger import get_kb_metadata, log_error, log_chat, log_path
import sqlite3

load_dotenv()

# -----------------------------------------
# Function: ask_question
# -----------------------------------------
def ask_question(goal_id, question, provider, api_key, model_name):

    """
    Accepts a user question and routes it to the appropriate LLM engine
    based on provider ("OpenAI (Paid)" vs. "Free (Beta)").
    """
    try:
        # Load user's vectorstore (indexed knowledge base)
        # 🧠 Resolve goal_id → kb_name
        conn = sqlite3.connect(log_path)
        c = conn.cursor()
        c.execute("SELECT kb_name FROM kb_meta WHERE goal_id = ?", (goal_id,))
        row = c.fetchone()
        conn.close()

        if not row:
            raise ValueError("Goal not found for provided goal_id")
        kb_name = row[0]
        # ✅ Load vectorstore using goal_id
        vectorstore = load_vectorstore(goal_id, provider, api_key)


        # --------------------------
        # OpenAI (Paid) routing
        # --------------------------
        if provider == "OpenAI (Paid)":
            llm = ChatOpenAI(
                temperature=0,
                model_name=model_name,
                openai_api_key=api_key
            )

        # --------------------------
        # Free model via Replicate
        # --------------------------
        else:
            import replicate

            class ReplicateLLM:
                def __init__(self, model_name="mistralai/mistral-7b-instruct-v0.1", temperature=0.3):
                    self.api_token = os.getenv("REPLICATE_API_TOKEN")
                    self.model = model_name
                    self.temperature = temperature

                def __call__(self, prompt, stop=None):
                    output = replicate.run(
                        self.model,
                        input={"prompt": prompt, "temperature": self.temperature},
                        api_token=self.api_token
                    )
                    return "".join(output)

            llm = ReplicateLLM(
                model_name="mistralai/mistral-7b-instruct-v0.1",
                temperature=0.3
            )

        # --------------------------
        # Run QA chain
        # --------------------------
        qa_chain = RetrievalQA.from_chain_type(
            llm=llm,
            retriever=vectorstore.as_retriever(),
            chain_type="stuff"
        )

        # Load correct KB metadata
        kb_meta = get_kb_metadata(goal_id, kb_name) 
        if kb_meta:
            prompt_context = f"""
The user is working on: '{kb_meta['intent']}'
Timeframe: {kb_meta['timeframe_value']} ({kb_meta['timeframe_type']})
Goal: {kb_meta['goal_description']}
Respond in a way that helps them move toward this goal.
"""
        else:
            prompt_context = ""

        full_prompt = prompt_context + "\n\n" + question
        answer = qa_chain.run(full_prompt)
        log_chat(goal_id, kb_meta["user_id"], question, answer)  # ✅ Log with user_id
        return answer

    except Exception as e:
        log_error("ask_question", str(e))
        return "⚠️ Sorry, I couldn’t process your question due to an internal error."
