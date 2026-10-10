import sys
import time

from langchain_core.runnables import RunnableLambda, RunnablePassthrough

from app import adapters
from app.cv_advisor import read_resume_text, suggest_improvements
from app.guardrails import check_input


class Blocked(Exception):
    pass


def _timed(name, fn):
    """wrap a step so we record how long it took (shown in the evaluation / UI)"""
    def run(state):
        t0 = time.time()
        out = fn(state)
        out.setdefault("timings", dict(state.get("timings", {})))
        out["timings"][name] = round(time.time() - t0, 2)
        return out
    return RunnableLambda(run)


def _guard(state):
    q = state.get("question")
    if q:
        r = check_input(q)
        if not r.allowed:
            raise Blocked(r.message)
    return state


def _parse(state):
    profile = adapters.parse(state["resume_path"])
    return {**state, "profile": profile}


def _match(state):
    return {**state, "jobs": adapters.match_jobs(state["resume_path"], k=5)}


def _advise(state):
    resume = read_resume_text(state["resume_path"])
    top_job = state["jobs"][0]["text"] if state["jobs"] else state.get("target_role", "")
    return {**state, "advice": suggest_improvements(resume, top_job)}


def _mentor(state):
    q = state.get("question")
    return {**state, "mentor": adapters.mentor_answer(q) if q else None}


workflow = (
    RunnablePassthrough()
    | RunnableLambda(_guard)
    | _timed("parse", _parse)
    | _timed("match", _match)
    | _timed("advise", _advise)
    | _timed("mentor", _mentor)
)


def run_pipeline(resume_path: str, question: str | None = None) -> dict:
    try:
        return workflow.invoke({"resume_path": resume_path, "question": question})
    except Blocked as e:
        return {"blocked": True, "message": str(e)}


if __name__ == "__main__":
    path = sys.argv[1] if len(sys.argv) > 1 else "data/resumes/My_Resume.pdf"
    question = sys.argv[2] if len(sys.argv) > 2 else None
    out = run_pipeline(path, question)

    if out.get("blocked"):
        print("BLOCKED:", out["message"])
    else:
        print("=== PROFILE ===");  print(adapters.profile_text(out["profile"])[:800])
        print("\n=== TOP JOBS ===")
        for j in out["jobs"]:
            print("-", j["title"])
        print("\n=== ADVICE ===");  print(out["advice"])
        if out["mentor"]:
            print("\n=== MENTOR ===");  print(out["mentor"])
        print("\nTimings (s):", out["timings"])
