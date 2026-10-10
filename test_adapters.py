from app import adapters as a

RESUME = "data/resumes/My_Resume.pdf"


def check(name, fn):
    print(f"\n--- {name} ---")
    try:
        out = fn()
        print("OK:", str(out)[:300])
    except Exception as e:
        print("FAILED:", type(e).__name__, "-", str(e)[:300])


check("1. parse", lambda: a.profile_text(a.parse(RESUME))[:200])
check("2. match_jobs", lambda: [j["title"] for j in a.match_jobs(RESUME, k=3)])
check("3. search_jobs", lambda: [j["title"] for j in a.search_jobs("docker jenkins ci cd", 3)])
check("4. kb_search", lambda: [t[:60] for t in a.kb_search("What should a fresher learn first?", 2)])
check("5. mentor_answer", lambda: a.mentor_answer("What is SmartHire?"))