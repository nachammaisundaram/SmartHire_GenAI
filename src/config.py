import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
RESUME_DIR = DATA_DIR / "resumes"
JOBS_DIR = DATA_DIR / "jobs"
NOTES_DIR = DATA_DIR / "career_notes"
VECTORSTORE_DIR = ROOT / "vectorstore"

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
LLM_MODEL = "gemini-3.5-flash-lite"
EMBED_MODEL = "models/gemini-embedding-001"

CHUNK_SIZE = 500
CHUNK_OVERLAP = 150
MAX_RETRIES = 2