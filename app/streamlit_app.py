import sys
import tempfile
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))

import streamlit as st
from src.parsing.resume_parser import parse_resume

st.title("SmartHire GenAI - Day 1")
file = st.file_uploader("Upload resume", type=["pdf", "docx"])

if file and st.button("Parse"):
    suffix = Path(file.name).suffix
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(file.getvalue())
    try:
        st.json(parse_resume(tmp.name).model_dump())
    except Exception as e:
        st.error(str(e))