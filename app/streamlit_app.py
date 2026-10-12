import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import streamlit as st

from src import adapters
from src.generate.cv_suggestions import (
    find_job_text,
    read_resume_text,
    rewrite_resume,
    suggest_improvements,
)
from src.safety.guardrails import check_input, check_output

st.set_page_config(page_title="SmartHire GenAI", layout="wide")

BLOCK_WORDS = ("unsafe", "injection", "off_topic")


# ---------- helpers ----------
def guard(text: str):
    """Returns (allowed, message). Runs guardrails before any LLM call."""
    res = check_input(text)
    for name in ("ok", "allowed", "safe", "passed"):
        if hasattr(res, name) and not getattr(res, name):
            return False, str(res)
    if any(w in str(res).lower() for w in BLOCK_WORDS):
        return False, str(res)
    return True, ""


def save_upload(uploaded) -> str:
    suffix = Path(uploaded.name).suffix
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(uploaded.getbuffer())
    return tmp.name


def need_resume() -> bool:
    if "resume_path" not in st.session_state:
        st.info("First 'Upload CV' page-la oru resume upload pannu.")
        return False
    return True


# ---------- pages ----------
def page_upload():
    st.header("Upload CV")
    uploaded = st.file_uploader("PDF or DOCX resume", type=["pdf", "docx"])
    if uploaded and st.button("Parse resume"):
        with st.spinner("Resume padichitu irukken..."):
            path = save_upload(uploaded)
            profile = adapters.parse(path)
        st.session_state.resume_path = path
        st.session_state.profile = profile
        st.session_state.pop("jobs", None)
        st.success("Parse aagiduchu.")

    profile = st.session_state.get("profile")
    if profile:
        data = profile.model_dump() if hasattr(profile, "model_dump") else {}
        st.subheader(data.get("name") or "Parsed profile")
        if data.get("email"):
            st.write(data["email"])
        if data.get("skills"):
            st.markdown("**Skills**")
            st.write(", ".join(data["skills"]))
        with st.expander("Full parsed profile (JSON)"):
            st.json(data)


def page_jobs():
    st.header("Matched Jobs")
    if not need_resume():
        return
    k = st.slider("How many jobs?", 3, 10, 5)
    if st.button("Find matching jobs"):
        with st.spinner("Semantic search nadakkudhu..."):
            st.session_state.jobs = adapters.match_jobs(
                st.session_state.resume_path, k
            )
    for i, job in enumerate(st.session_state.get("jobs", []), start=1):
        with st.expander(f"{i}. {job['title']}"):
            st.write(job["text"])


def page_cv():
    st.header("CV Suggestions")
    if not need_resume():
        return
    role = st.text_input("Target role", placeholder="e.g. Data Analyst")
    col1, col2 = st.columns(2)
    do_suggest = col1.button("Get suggestions")
    do_rewrite = col2.button("Rewrite my resume")

    if (do_suggest or do_rewrite) and role.strip():
        ok, msg = guard(role)
        if not ok:
            st.error(f"Indha input accept panna mudiyaadhu. ({msg})")
            return
        resume_text = read_resume_text(st.session_state.resume_path)
        job_text = find_job_text(role)
        if do_suggest:
            with st.spinner("Suggestions ready aagudhu..."):
                text, flags = check_output(
                    suggest_improvements(resume_text, job_text)
                )
            st.session_state.suggestions = text
            st.session_state.flags = flags
        if do_rewrite:
            with st.spinner("Resume rewrite aagudhu..."):
                st.session_state.rewrite = rewrite_resume(resume_text, job_text)
    elif (do_suggest or do_rewrite):
        st.warning("Target role type pannu.")

    if st.session_state.get("suggestions"):
        st.subheader("Suggestions")
        st.markdown(st.session_state.suggestions)
        if st.session_state.get("flags"):
            st.warning(f"Output check flags: {st.session_state.flags}")

    if st.session_state.get("rewrite"):
        st.subheader("Rewritten resume")
        rw = st.session_state.rewrite
        if isinstance(rw, dict):
            for key, val in rw.items():
                st.markdown(f"**{key}**")
                st.write(val)
        else:
            st.write(rw)


def page_mentor():
    st.header("AI Career Mentor")
    st.session_state.setdefault("chat", [])
    for role, text in st.session_state.chat:
        with st.chat_message(role):
            st.write(text)

    q = st.chat_input("Career question kelu...")
    if q:
        st.session_state.chat.append(("user", q))
        with st.chat_message("user"):
            st.write(q)
        ok, msg = guard(q)
        if ok:
            with st.spinner("Notes-la thedikitu irukken..."):
                answer = adapters.mentor_answer(q)
        else:
            answer = "Naan career-related questions-ku mattum dhaan help panna mudiyum."
        st.session_state.chat.append(("assistant", answer))
        with st.chat_message("assistant"):
            st.write(answer)


# ---------- layout ----------
PAGES = {
    "Upload CV": page_upload,
    "Matched Jobs": page_jobs,
    "CV Suggestions": page_cv,
    "Career Mentor": page_mentor,
}

with st.sidebar:
    st.title("SmartHire GenAI")
    st.caption("Resume matching & AI career mentor")
    choice = st.radio("Go to", list(PAGES.keys()))

PAGES[choice]()