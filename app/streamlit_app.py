import sys
import html
import re
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

st.markdown(
    """
<style>
/* ---- Sidebar width ---- */
[data-testid="stSidebar"] {
    min-width: 340px;
    width: 340px;
}

/* ---- Top spacing ---- */
[data-testid="stSidebarUserContent"] {
    padding-top: 3rem;
    padding-left: 0.8rem;
}

/* ---- Title: "SmartHire GenAI" ---- */
[data-testid="stSidebar"] h1 {
    font-size: 2.4rem;
    line-height: 1.25;
    margin-bottom: 0.4rem;
}

/* ---- Caption: "Resume matching & AI career mentor" ---- */
[data-testid="stSidebar"] [data-testid="stCaptionContainer"] p {
    font-size: 1.1rem;
    line-height: 1.6;
    margin-bottom: 2.5rem;
}

/* ---- "Go to" label ---- */
[data-testid="stSidebar"] [data-testid="stWidgetLabel"] p {
    font-size: 1.15rem;
    margin-bottom: 1rem;
}

/* ---- Menu items ---- */
[data-testid="stSidebar"] div[role="radiogroup"] {
    gap: 1.3rem;
}
[data-testid="stSidebar"] div[role="radiogroup"] label p {
    font-size: 1.35rem;
    line-height: 1.6;
}

/* ---- Bigger radio circles ---- */
[data-testid="stSidebar"] div[role="radiogroup"] label > div:first-child {
    transform: scale(1.3);
    margin-right: 0.6rem;
}

/* ---- All main buttons (Parse resume, Find jobs, Get suggestions...) ---- */
.stButton > button {
    background-color: #6B7A2F;
    color: #FAF3E0;
    border: none;
    border-radius: 8px;
    padding: 0.6rem 1.6rem;
    font-weight: 600;
}
.stButton > button p {
    color: #FAF3E0;
    font-size: 1.05rem;
}
.stButton > button:hover {
    background-color: #3F4A1C;
    color: #FAF3E0;
}

/* ---- File uploader "Upload" button ---- */
[data-testid="stFileUploaderDropzone"] button[data-testid="stBaseButton-secondary"] {
    background-color: #3F4A1C;
    color: #FAF3E0;
    border: none;
    border-radius: 8px;
}
[data-testid="stFileUploaderDropzone"] button[data-testid="stBaseButton-secondary"]:hover {
    background-color: #6B7A2F;
    color: #FAF3E0;
}

/* ---- Slider label ---- */
[data-testid="stSlider"] label p {
    font-size: 1.25rem;
    font-weight: 600;
    margin-bottom: 0.6rem;
}

/* ---- Job cards (expander) ---- */
[data-testid="stExpander"] summary p {
    font-size: 1.15rem;
    font-weight: 600;
}
[data-testid="stExpander"] [data-testid="stMarkdownContainer"] p {
    font-size: 1.05rem;
    line-height: 1.7;
}

/* ---- Skill chips ---- */
.skill-chip {
    display: inline-block;
    background-color: #3F4A1C;
    color: #F5EFD8;
    padding: 0.3rem 0.85rem;
    margin: 0.25rem 0.4rem 0.25rem 0;
    border-radius: 999px;
    font-size: 0.95rem;
}

</style>
""",
    unsafe_allow_html=True,
)

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
        st.info("Please upload your resume on the Upload CV page first.")
        return False
    return True


# ---------- pages ----------
def page_upload():
    st.header("Upload CV")
    uploaded = st.file_uploader("Upload your resume (PDF or DOCX)", type=["pdf", "docx"])
    if uploaded and st.button("Parse resume"):
        with st.spinner("Reading your resume..."):
            path = save_upload(uploaded)
            profile = adapters.parse(path)
        st.session_state.resume_path = path
        st.session_state.profile = profile
        st.session_state.pop("jobs", None)
        st.success("Resume parsed successfully.")

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

    
JOB_KEYS = ("title", "company", "location", "skills", "score")


def parse_job_text(text: str) -> dict:
    """Splits 'title: X company: Y location: Z skills: ... score: 0.4' into fields."""
    pattern = r"(title|company|location|skills|score):\s*(.*?)(?=\s+(?:title|company|location|skills|score):|$)"
    return {k: v.strip() for k, v in re.findall(pattern, text, flags=re.S)}

def diversify(jobs: list[dict]) -> list[dict]:
    """Keep only the best-ranked job for each title + company + location."""
    seen, unique = set(), []
    for job in jobs:
        info = parse_job_text(job["text"])
        key = (info.get("title"), info.get("company"), info.get("location"))
        if key in seen:
            continue
        seen.add(key)
        unique.append(job)
    return unique


def page_jobs():
    st.header("Matched Jobs")
    if not need_resume():
        return

    k = st.slider("Number of job matches to display", 3, 10, 5)

    if st.button("Find matching jobs"):
        with st.spinner("Finding the best job matches for your profile..."):
            st.session_state.jobs = diversify(
                adapters.match_jobs(st.session_state.resume_path, k * 6)
            )[:k]

    jobs = st.session_state.get("jobs", [])
    for i, job in enumerate(jobs, start=1):
        info = parse_job_text(job["text"])
        title = info.get("title") or job["title"]
        company = info.get("company", "")
        label = f"{i}. {title}" + (f"  |  {company}" if company else "")

        with st.expander(label):
            if not info:
                st.write(job["text"])
                continue

            c1, c2 = st.columns(2)
            c1.markdown(f"**Company**  \n{info.get('company', '-')}")
            c2.markdown(f"**Location**  \n{info.get('location', '-')}")

            skills = [s.strip() for s in info.get("skills", "").split(",") if s.strip()]
            if skills:
                st.markdown("**Required skills**")
                chips = "".join(
                    f'<span class="skill-chip">{html.escape(s)}</span>' for s in skills
                )
                st.markdown(chips, unsafe_allow_html=True)

           
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
            st.error(f"This request cannot be processed. ({msg})")
            return
        resume_text = read_resume_text(st.session_state.resume_path)
        job_text = find_job_text(role)
        if do_suggest:
            with st.spinner("Generating CV suggestions..."):
                text, flags = check_output(
                    suggest_improvements(resume_text, job_text)
                )
            st.session_state.suggestions = text
            st.session_state.flags = flags
        if do_rewrite:
            with st.spinner("Rewriting your resume for the target role..."):
                st.session_state.rewrite = rewrite_resume(resume_text, job_text)
    elif (do_suggest or do_rewrite):
        st.warning("Please enter a target role.")

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

    q = st.chat_input("Ask a career question...")
    if q:
        st.session_state.chat.append(("user", q))
        with st.chat_message("user"):
            st.write(q)
        ok, msg = guard(q)
        if ok:
            with st.spinner("	Searching career notes..."):
                answer = adapters.mentor_answer(q)
        else:
            answer = "I can only help with career-related questions."
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