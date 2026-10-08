import os
import time
import pandas as pd
from langchain_core.documents import Document
from langchain_community.vectorstores import FAISS
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from dotenv import load_dotenv

load_dotenv()

EMBED_MODEL = "models/gemini-embedding-001"
INDEX_DIR = "data/faiss_jobs_gemini"

embeddings = GoogleGenerativeAIEmbeddings(model=EMBED_MODEL)


def load_jobs(csv_path):
    df = pd.read_csv(csv_path).fillna("")
    docs = []
    for _, row in df.iterrows():
        text = f"{row['title']}. Skills: {row['skills']}. {row['description']}"
        docs.append(Document(
            page_content=text,
            metadata={"job_id": row["job_id"], "title": row["title"],
                      "company": row["company"], "location": row["location"],
                      "skills": row["skills"]},
        ))
    return docs


def build_index(csv_path, batch_size=90, wait=65):
    docs = load_jobs(csv_path)
    db = None
    for i in range(0, len(docs), batch_size):
        batch = docs[i:i + batch_size]
        if db is None:
            db = FAISS.from_documents(batch, embeddings)
        else:
            db.add_documents(batch)
        print(f"Embedded {min(i + batch_size, len(docs))}/{len(docs)}")
        if i + batch_size < len(docs):
            print(f"Waiting {wait}s for free-tier quota...")
            time.sleep(wait)
    db.save_local(INDEX_DIR)
    return db


def load_index():
    return FAISS.load_local(INDEX_DIR, embeddings, allow_dangerous_deserialization=True)


def search_jobs(query, k=5):
    db = load_index()
    results = db.similarity_search_with_score(query, k=k)
    return [{"title": d.metadata["title"], "company": d.metadata["company"],
             "location": d.metadata["location"], "skills": d.metadata["skills"],
             "score": round(float(s), 3)}
            for d, s in results]

def build_resume_query(profile):
    d = profile.model_dump()
    parts = []
    if d.get("target_role"):
        parts.append(f"Target role: {d['target_role']}.")
    if d.get("skills"):
        parts.append("Skills: " + ", ".join(d["skills"]) + ".")
    if d.get("summary"):
        parts.append(d["summary"])
    for e in d.get("experience", []):
        parts.append(f"{e.get('role', '')}. " + " ".join(e.get("highlights", [])))
    return " ".join(parts)


def jobs_for_resume(resume_path, k=5):
    from src.parsing.resume_parser import parse_resume
    profile = parse_resume(resume_path)
    return search_jobs(build_resume_query(profile), k=k)

if __name__ == "__main__":
    if not os.path.exists(INDEX_DIR):
        build_index("data/jobs.csv")
        print("Index built.")
    for q in ["python backend developer", "docker kubernetes aws jenkins",
              "fresher who knows langchain and rag", "sql and power bi reports"]:
        print("\nQUERY:", q)
        for r in search_jobs(q):
            print(" ", r["score"], "|", r["title"], "|", r["company"], "|", r["location"])