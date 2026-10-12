# SmartHire GenAI

SmartHire GenAI is a small career portal I built as my Generative AI capstone project. You upload your resume, and it reads it, finds jobs that match your profile, suggests how to improve your CV for a role you pick, and lets you ask career questions to an AI mentor.

I built this on my own over about three weeks, as part of my Gen AI internship training.

Live demo: _I will add the link here once it is deployed_

## What it does

- **Upload CV:** reads a PDF or DOCX resume and pulls out the name, email, skills, education and experience.
- **Matched Jobs:** compares your profile with a set of job postings by meaning (not just keywords) and shows the closest ones.
- **CV Suggestions:** you type a target role, and it tells you what is missing in your CV. It can also rewrite your resume for that role without adding skills or numbers you never had.
- **Career Mentor:** a chatbot that answers career questions only from my career notes. If the answer is not in the notes, it says so instead of guessing.

There is also a guardrails layer. It blocks unsafe requests (like asking it to add fake experience), prompt injection, and off-topic questions before anything reaches the model.

## How it works

1. The resume is loaded and split into chunks, then the LLM turns it into a clean JSON profile.
2. The profile is embedded and searched against a FAISS index of job descriptions to get the top matches.
3. For suggestions, the resume and a matching job description go into a prompt from my prompt library.
4. The mentor uses RAG: it finds the most relevant parts of my career notes and answers from those.
5. Guardrails check the input before every LLM call.

I used Gemini (`gemini-3.5-flash-lite`) for the LLM, `gemini-embedding-001` for embeddings, FAISS for the vector store, LangChain for the mentor, and Streamlit for the UI.

## Project structure

```
SmartHire_GenAI/
├── app/streamlit_app.py     # the portal
├── src/
│   ├── config.py            # model names and paths
│   ├── adapters.py          # simple functions the UI calls
│   ├── llm_util.py          # LLM helper with retries
│   ├── workflow.py          # parse -> match -> advise pipeline
│   ├── evaluate.py          # evaluation code
│   ├── parsing/             # resume loader and parser
│   ├── search/              # embeddings and job search
│   ├── generate/            # prompts and CV suggestions
│   ├── mentor/              # RAG mentor
│   └── safety/              # guardrails
├── data/                    # jobs, sample resumes, career notes, FAISS indexes
├── notebooks/               # my experiments
├── eval_results/            # evaluation reports
├── scripts/                 # small helper scripts
├── tests/                   # quick checks
├── .streamlit/config.toml   # theme colours
├── requirements.txt
└── .env.example
```

## Running it locally

You need Python 3.12 or 3.13 and a Gemini API key.

```powershell
git clone <repo-url>
cd SmartHire_GenAI
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Copy `.env.example` to `.env` and put your key in it:

```
GEMINI_API_KEY=your_key_here
```

Then start the app:

```powershell
python -m streamlit run app\streamlit_app.py
```

It opens at http://localhost:8501. There are a few sample resumes in `data/resumes/` you can try.

To run the quick tests, use these from the project root:

```powershell
python -m tests.test_day1
python -m tests.test_adapters
python -m tests.test_guard
```

## Evaluation

I did not want to just demo it, so I tested it. The reports are in `eval_results/` and cover:

- whether the top jobs are actually relevant for sample profiles
- how good the mentor's answers are (correct, grounded in the notes, helpful)
- a before and after comparison of a prompt I improved
- whether the mentor refuses when the answer is not in the documents

## Things to know

- The jobs come from a dataset I prepared, not from live LinkedIn or Naukri scraping, because that is against their terms.
- The dataset is synthetic, so many jobs share the same title, company and location with different skills. The portal shows only the best match for each, so you do not see the same job repeated.
- The mentor only knows what is in my career notes, so it will not answer everything.
- Guardrails help, but they are not a perfect safety system.
- The free Gemini API has limits, so very heavy use can slow down or fail.

## About me

S. Nachammai, final-year MCA student.
