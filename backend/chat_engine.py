# File: backend/chat_engine.py

from backend.embedder import load_vectorstore
from langchain.chains import RetrievalQA
from langchain.chat_models import ChatOpenAI

# Create a single shared instance of the language model
# GPT-4o or GPT-3.5 can be used here
llm = ChatOpenAI(
    temperature=0,                 # 0 = deterministic, consistent answers
    model_name="gpt-4-1106-preview"  # You can change this to "gpt-3.5-turbo" if needed
)

# -----------------------------------------
# Function: ask_question
# -----------------------------------------
def ask_question(question, namespace):
    """
    Accepts a user question and retrieves the most relevant content chunks
    from that user's session vector DB. Then asks OpenAI to answer based on it.

    Parameters:
    - question: the user’s input string
    - namespace: session ID to load the right content

    Returns:
    - GPT-generated response using relevant knowledge
    """
    # Load vector store for this user's content
    vectorstore = load_vectorstore(namespace)

    # Create a Retrieval-based QA chain using that vector store
    qa_chain = RetrievalQA.from_chain_type(
        llm=llm,
        retriever=vectorstore.as_retriever(),  # Semantic search engine
        chain_type="stuff"  # Stuff = inject chunks directly into prompt
    )

    # Run the chain with the user’s question
    return qa_chain.run(question)
