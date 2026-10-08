import os
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings
from app.job_search import load_jobs, load_index

MINI_DIR = "data/faiss_jobs_minilm"
mini = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")

if not os.path.exists(MINI_DIR):
    FAISS.from_documents(load_jobs("data/jobs.csv"), mini).save_local(MINI_DIR)

gemini_db = load_index()
mini_db = FAISS.load_local(MINI_DIR, mini, allow_dangerous_deserialization=True)

queries = ["python backend developer", "docker kubernetes aws jenkins",
           "fresher who knows langchain and rag", "sql and power bi reports",
           "testing web apps with selenium"]

for q in queries:
    print("\nQUERY:", q)
    print(" Gemini:", [d.metadata["title"] for d, _ in gemini_db.similarity_search_with_score(q, k=3)])
    print(" MiniLM:", [d.metadata["title"] for d, _ in mini_db.similarity_search_with_score(q, k=3)])