r"""
ADAPTERS - the ONLY file that touches your Day 1-3 code.
Day 4/5 modules (workflow.py, evaluation.py) call only the functions below.

Your real functions (from grep):
  src/parsing/resume_parser.py : parse_resume(path) -> ResumeProfile
  app/job_search.py            : search_jobs(query, k=5), jobs_for_resume(resume_path, k=5)
  app/career_mentor.py         : get_db(), retrieve(db, query, k), ask(db, question, history)
"""
from app import career_mentor as cm
from app import job_search as js
from src.parsing.resume_parser import parse_resume


def _text_of(item) -> str:
    """Search hit -> plain text. Handles (Document, score), Document, dict, or str."""
    if isinstance(item, tuple):
        item = item[0]
    if hasattr(item, "page_content"):
        return item.page_content
    if isinstance(item, dict):
        return "\n".join(f"{k}: {v}" for k, v in item.items())
    return str(item)


def _title_of(item) -> str:
    if isinstance(item, tuple):
        item = item[0]
    meta = getattr(item, "metadata", None) or (item if isinstance(item, dict) else {})
    return str(meta.get("title") or meta.get("job_title") or _text_of(item)[:60])


# ---- 1. parse resume --------------------------------------------------------
def parse(path: str):
    """-> ResumeProfile (Pydantic)"""
    return parse_resume(path)


def profile_text(profile) -> str:
    return profile.model_dump_json(indent=2) if hasattr(profile, "model_dump_json") else str(profile)


# ---- 2. jobs ----------------------------------------------------------------
def match_jobs(resume_path: str, k: int = 5) -> list[dict]:
    hits = js.jobs_for_resume(resume_path, k)
    return [{"title": _title_of(h), "text": _text_of(h)} for h in list(hits)[:k]]


def search_jobs(query: str, k: int = 3) -> list[dict]:
    hits = js.search_jobs(query, k)
    return [{"title": _title_of(h), "text": _text_of(h)} for h in list(hits)[:k]]


# ---- 3. career KB + mentor --------------------------------------------------
_db = None


def _get_db():
    global _db
    if _db is None:
        _db = cm.get_db()
    return _db


def kb_search(query: str, k: int = 3) -> list[str]:
    hits = cm.retrieve(_get_db(), query, k)
    return [_text_of(h) for h in list(hits)[:k]]


def mentor_answer(question: str) -> str:
    """Single-turn call: empty history each time, so evaluation answers don't affect each other."""
    res = cm.ask(_get_db(), question, [])
    if isinstance(res, dict):
        for key in ("answer", "response", "text", "output"):
            if key in res:
                return str(res[key])
    if isinstance(res, (tuple, list)) and res:
        return str(res[0])
    return str(res)
