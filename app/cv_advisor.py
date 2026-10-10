import csv
import sys

from langchain_community.document_loaders import Docx2txtLoader, PyPDFLoader
from langchain_core.output_parsers import StrOutputParser

from app.guardrails import check_output, check_rewrite_faithfulness, load_skill_vocab
from app.llm_util import get_llm, safe_invoke
from app.prompts import PROMPTS


# ------------------------------------------------------------------ helpers
def read_resume_text(path: str) -> str:
    loader = PyPDFLoader(path) if path.lower().endswith(".pdf") else Docx2txtLoader(path)
    return "\n".join(d.page_content for d in loader.load())


def find_job_text(role: str, jobs_csv: str = "data/jobs.csv") -> str:
    """First job in jobs.csv whose title contains `role`. Falls back to using the role text itself."""
    try:
        with open(jobs_csv, encoding="utf-8") as f:
            for row in csv.DictReader(f):
                if role.lower() in row.get("title", "").lower():
                    return (f"{row['title']} at {row.get('company', '')}\n"
                            f"Skills: {row.get('skills', '')}\n{row.get('description', '')}")
    except FileNotFoundError:
        pass
    return role


# ------------------------------------------------------------------ CV suggestions
def suggest_improvements(resume_text: str, job_text: str, version: str = "v2") -> str:
    chain = PROMPTS[f"cv_suggest_{version}"] | get_llm() | StrOutputParser()
    text = safe_invoke(chain, {"resume": resume_text, "job": job_text})
    text, _warnings = check_output(text)
    return text


# ------------------------------------------------------------------ rewrite my resume
def rewrite_resume(resume_text: str, job_text: str) -> dict:
    """
    1) rewrite  2) faithfulness check (new numbers / new skills?)  3) if flagged -> one fix pass  4) re-check.
    Returns dict(resume=..., report=..., fixed=bool, warnings=[...])
    """
    llm = get_llm()
    vocab = load_skill_vocab()

    draft = safe_invoke(PROMPTS["rewrite_resume_v1"] | llm | StrOutputParser(),
                        {"resume": resume_text, "job": job_text})
    report = check_rewrite_faithfulness(resume_text, draft, vocab)
    fixed = False

    if not report["ok"]:
        issues = ", ".join(report["new_numbers"] + report["new_skills"])
        draft = safe_invoke(PROMPTS["rewrite_fix_v1"] | llm | StrOutputParser(),
                            {"resume": resume_text, "draft": draft, "issues": issues})
        report = check_rewrite_faithfulness(resume_text, draft, vocab)
        fixed = True

    draft, warnings = check_output(draft)
    if not report["ok"]:
        warnings.append("Some items may still be new: " + ", ".join(report["new_numbers"] + report["new_skills"])
                        + " - please verify each one before using this resume.")
    return {"resume": draft, "report": report, "fixed": fixed, "warnings": warnings}


# ------------------------------------------------------------------ test run
if __name__ == "__main__":
    path = sys.argv[1] if len(sys.argv) > 1 else "data/resumes/My_Resume.pdf"
    role = sys.argv[2] if len(sys.argv) > 2 else "DevOps"
    resume = read_resume_text(path)
    job = find_job_text(role)

    print("=== CV SUGGESTIONS ===")
    print(suggest_improvements(resume, job))

    print("\n=== REWRITTEN RESUME ===")
    out = rewrite_resume(resume, job)
    print(out["resume"])
    print("\nFaithfulness:", out["report"], "| fix pass used:", out["fixed"])
    for w in out["warnings"]:
        print("WARNING:", w)
