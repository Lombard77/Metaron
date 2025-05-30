# File: backend/embedder.py

import os
from pathlib import Path
from dotenv import load_dotenv

from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma

from logger import log_error, log
job_progress = {}  # 🔁 Tracks job status by job_id


load_dotenv()  # Ensures .env is loaded if this file is run/imported

# Directory where your vector database files will be stored
chroma_dir = "data/vector_store"

# This uses OpenAI's & HuggingFace embedding models      
def get_embedding_function(provider, api_key):
    if provider == "OpenAI (Additional AI Costs)":
        return OpenAIEmbeddings(openai_api_key=api_key)
    else:
        return HuggingFaceEmbeddings(model_name="BAAI/bge-small-en")

# -----------------------------------------
# Function: embed_and_store
# -----------------------------------------
def embed_and_store(text, goal_id, provider, api_key=None, job_id=None):
    """
    Takes raw text and:
    - Splits it into smaller chunks
    - Embeds those chunks using OpenAI or HuggingFace
    - Stores them in a Chroma vector DB using the provided namespace

    Parameters:
    - text: full cleaned text to index
    - namespace: unique session ID or user ID (keeps each tutor’s data isolated)
    """
    try:
        print(f"🧾 Text length received: {len(text)} characters")
        if job_id:
            job_progress[job_id] = "parsing"
            print(f"🧪 [job {job_id}] → Status: parsing")


        text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100)
        docs = text_splitter.create_documents([text])
        print(f"📦 Chunks created: {len(docs)}")

        print("🧪 Getting embedding function...")
        try:
            embedding_function = get_embedding_function(provider, api_key)
            print("✅ Embedding function loaded.")
            if job_id:
                job_progress[job_id] = "embedding"
                print(f"🧠 [job {job_id}] → Status: embedding")
        except Exception as embed_init_err:
            print("❌ Embedding function init failed:", embed_init_err)
            raise RuntimeError("❌ Could not initialize embedding function.")
        if job_id:
            job_progress[job_id] = "finalizing"
            print(f"🔧 [job {job_id}] → Status: finalizing")
        print("🧪 Initializing Chroma DB...")
        db = Chroma(
            collection_name=goal_id,
            persist_directory=chroma_dir,
            embedding_function=embedding_function,
        )
        print("✅ Chroma DB initialized.")

        print("🧪 Adding documents to DB...")
        try:
            db.add_documents(docs)
            print("✅ Documents added to DB.")
        except Exception as embed_error:
            print("❌ EMBEDDING CRASHED:", embed_error)
            raise RuntimeError("❌ Embedding add_documents failed.")

        print("💾 Persisting DB...")
        db.persist()
        if job_id:
            job_progress[job_id] = "complete"
            print(f"✅ [job {job_id}] → Status: complete")
        print("✅ DB persisted successfully.")

    except Exception as e:
        print("⚠️ General embed_and_store error:", e)
        raise RuntimeError("⚠️ Embedding failed. Check logs for details.")


# -----------------------------------------
# Function: load_vectorstore
# -----------------------------------------
def load_vectorstore(namespace, provider, api_key):
    """
    Loads the stored vector database (for retrieval during chat).
    Parameters:
    - namespace: session ID or user ID (same as used in embed_and_store)
    Returns:
    - A Chroma vector store ready for semantic search
    """
    embedding_function = get_embedding_function(provider, api_key)

    return Chroma(
        collection_name=namespace,
        persist_directory=chroma_dir,
        embedding_function=embedding_function,
    )

def build_engine():
    embedding_function = HuggingFaceEmbeddings(model_name="BAAI/bge-small-en")
    return Chroma(
        persist_directory="data/vector_store",
        embedding_function=embedding_function
    )
