# File: backend/embedder.py

import os
from langchain.embeddings import OpenAIEmbeddings
from langchain.vectorstores import Chroma
from langchain.text_splitter import RecursiveCharacterTextSplitter

# Directory where your vector database files will be stored
chroma_dir = "data/vector_store"

# This uses OpenAI's embedding model (you can swap for others later)
embedding_function = OpenAIEmbeddings()

# -----------------------------------------
# Function: embed_and_store
# -----------------------------------------
def embed_and_store(text, namespace):
    """
    Takes raw text and:
    - Splits it into smaller chunks
    - Embeds those chunks using OpenAI
    - Stores them in a Chroma vector DB using the provided namespace (session_id)

    Parameters:
    - text: full cleaned text to index
    - namespace: unique session ID or user ID (keeps each tutor’s data isolated)
    """

    # Split text into chunks (~1000 characters) with some overlap for context
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100)
    docs = text_splitter.create_documents([text])

    # Create or load a Chroma vector DB under the given namespace (session ID)
    db = Chroma(
        collection_name=namespace,
        persist_directory=chroma_dir,
        embedding_function=embedding_function,
    )

    # Add all document chunks to the vector DB
    db.add_documents(docs)
    db.persist()  # Saves to disk

# -----------------------------------------
# Function: load_vectorstore
# -----------------------------------------
def load_vectorstore(namespace):
    """
    Loads the stored vector database (for retrieval during chat).
    Parameters:
    - namespace: session ID or user ID (same as used in embed_and_store)
    Returns:
    - A Chroma vector store ready for semantic search
    """
    return Chroma(
        collection_name=namespace,
        persist_directory=chroma_dir,
        embedding_function=embedding_function,
    )
