import glob
import json
import os
import sys
import time

from langchain_core.output_parsers import JsonOutputParser, StrOutputParser

from app import adapters
from app.cv_advisor import find_job_text, read_resume_text, rewrite_resume, suggest_improvements
from app.llm_util import get_llm, safe_invoke
from app.prompts import PROMPTS

PAUSE = 4
OUT_DIR = "eval_results"

# ------------------------------------------------------------------ test sets (EDIT these to your own)
# (query, keyword that must appear in a top-k hit)
JOB_TESTS = [
    ("docker jenkins ci cd pipeline", "devops"),
    ("python machine learning model training", "machine learning"),
    ("langchain rag chatbot llm", "gen"),
    ("sql dashboards power bi", "data"),
    ("react node full stack web app", "full"),
]
KB_TESTS = [
    ("What should a fresher learn first for Gen AI?", "fresher"),
    ("How do I prepare for a RAG interview?", "rag"),
    ("What is SmartHire?", "smarthire"),
    ("Should I do a Ph.D. after MCA?", "ph"),
    ("How to show DevOps experience in a Gen AI resume?", "devops"),
]
ANSWER_QUESTIONS = [
    "What should I learn first to become a Gen AI engineer?",
    "How do I explain my DevOps internship in a Gen AI interview?",
    "What projects should a fresher put on a Gen AI portfolio?",
    "How do I prepare for UGC NET while working?",
]
# questions the KB cannot answer -> a good mentor says it does not know
OUT_OF_KB = [
    "What is the exact salary of a Gen AI intern at Zoho?",
    "Who won the cricket world cup in 2011?",
    "Which company will definitely hire me next month?",
]
REFUSAL_HINTS = ["don't have", "do not have", "not in my", "not sure", "no information", "can't confirm",
                 "cannot confirm", "not available", "outside", "can't guarantee", "cannot guarantee"]


# ------------------------------------------------------------------ helpers
def _judge(prompt_name: str, inputs: dict) -> dict:
    chain = PROMPTS[prompt_name] | get_llm() | JsonOutputParser()
    try:
        out = safe_invoke(chain, inputs)
    except Exception as e:  # noqa: BLE001
        out = {"error": str(e)[:80]}
    time.sleep(PAUSE)
    return out


def _avg(rows, key):
    vals = [r[key] for r in rows if isinstance(r.get(key), (int, float))]
    return round(sum(vals) / len(vals), 2) if vals else None


def _table(headers, rows):
    lines = ["| " + " | ".join(headers) + " |", "|" + "---|" * len(headers)]
    lines += ["| " + " | ".join(str(c) for c in r) + " |" for r in rows]
    return "\n".join(lines)


# ------------------------------------------------------------------ 1. retrieval hit rate
def eval_retrieval(k: int = 3) -> str:
    out = ["## 1. Retrieval hit rate (top-%d)\n" % k]
    for label, tests, fn in [("Job search", JOB_TESTS, adapters.search_jobs),
                             ("Career KB", KB_TESTS, adapters.kb_search)]:
        rows, hits = [], 0
        for q, kw in tests:
            res = fn(q, k)
            texts = [(r["title"] + " " + r["text"]) if isinstance(r, dict) else r for r in res]
            rank = next((i + 1 for i, t in enumerate(texts) if kw.lower() in t.lower()), None)
            hits += rank is not None
            rows.append([q, kw, rank or "miss"])
            time.sleep(1)
        out.append(f"**{label}: {hits}/{len(tests)} = {hits / len(tests):.0%}**\n")
        out.append(_table(["query", "expected keyword", "rank found"], rows) + "\n")
    return "\n".join(out)


# ------------------------------------------------------------------ 2. answer quality
def eval_answers() -> str:
    rows = []
    for q in ANSWER_QUESTIONS:
        ctx = "\n---\n".join(adapters.kb_search(q, 3))
        ans = adapters.mentor_answer(q)
        time.sleep(PAUSE)
        s = _judge("judge_answer_v1", {"question": q, "context": ctx, "answer": ans})
        rows.append({"q": q, **s})
        print("answers:", q[:50], s)
    table = _table(["question", "relevance", "groundedness", "actionability", "comment"],
                   [[r["q"][:45], r.get("relevance"), r.get("groundedness"), r.get("actionability"),
                     str(r.get("comment", r.get("error", "")))[:70]] for r in rows])
    avg = f"Average: relevance {_avg(rows, 'relevance')}, groundedness {_avg(rows, 'groundedness')}, actionability {_avg(rows, 'actionability')}"
    return f"## 2. Mentor answer quality (LLM judge, 1-5)\n\n{table}\n\n**{avg}**\n"


# ------------------------------------------------------------------ 3. prompt before / after
def eval_prompts(role: str = "DevOps") -> str:
    resumes = sorted(glob.glob("data/resumes/*.pdf") + glob.glob("data/resumes/*.docx"))[:5]
    job = find_job_text(role)
    res = {"v1": [], "v2": []}
    for path in resumes:
        resume = read_resume_text(path)
        for v in ("v1", "v2"):
            ans = suggest_improvements(resume, job, version=v)
            time.sleep(PAUSE)
            s = _judge("judge_cv_v1", {"resume": resume, "job": job, "answer": ans})
            res[v].append(s)
            print("prompts:", os.path.basename(path), v, s)
    keys = ["specificity", "grounded", "actionable", "structure"]
    rows = [[k, _avg(res["v1"], k), _avg(res["v2"], k)] for k in keys]
    return (f"## 3. Prompt before / after (cv_suggest v1 vs v2, {len(resumes)} resumes, 1-5)\n\n"
            + _table(["criterion", "v1 (before)", "v2 (after)"], rows) + "\n")


# ------------------------------------------------------------------ 4. hallucination checks
def eval_hallucination() -> str:
    out = ["## 4. Hallucination checks\n"]

    # (a) rewrite faithfulness
    resumes = sorted(glob.glob("data/resumes/*.pdf") + glob.glob("data/resumes/*.docx"))[:5]
    rows = []
    for path in resumes:
        r = rewrite_resume(read_resume_text(path), find_job_text("Gen"))
        rows.append([os.path.basename(path), "yes" if r["fixed"] else "no",
                     ", ".join(r["report"]["new_numbers"] + r["report"]["new_skills"]) or "none"])
        time.sleep(PAUSE)
    out.append("**(a) Rewrite my resume: invented numbers/skills after the guard**\n")
    out.append(_table(["resume", "needed fix pass", "still-new items"], rows) + "\n")

    # (b) questions outside the KB
    rows, good = [], 0
    for q in OUT_OF_KB:
        ans = adapters.mentor_answer(q)
        time.sleep(PAUSE)
        refused = any(h in ans.lower() for h in REFUSAL_HINTS)
        good += refused
        rows.append([q, "yes" if refused else "NO - check", ans[:80].replace("\n", " ")])
    out.append(f"**(b) Out-of-KB questions: mentor admitted it does not know {good}/{len(OUT_OF_KB)}**\n")
    out.append(_table(["question", "admitted not knowing", "answer start"], rows) + "\n")
    return "\n".join(out)


# ------------------------------------------------------------------ main
PARTS = {"retrieval": eval_retrieval, "answers": eval_answers,
         "prompts": eval_prompts, "hallucination": eval_hallucination}

if __name__ == "__main__":
    chosen = sys.argv[1:] or list(PARTS)
    os.makedirs(OUT_DIR, exist_ok=True)
    sections = []
    for name in chosen:
        print(f"\n##### running {name} #####")
        sections.append(PARTS[name]())
    report = "# SmartHire Evaluation Report\n\n" + "\n".join(sections)
    path = os.path.join(OUT_DIR, "report.md" if len(chosen) == len(PARTS) else f"report_{'_'.join(chosen)}.md")
    with open(path, "w", encoding="utf-8") as f:
        f.write(report)
    print(report)
    print(f"\nSaved to {path}")
