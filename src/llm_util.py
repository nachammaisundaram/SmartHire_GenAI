import time

from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI

load_dotenv()

LLM_MODEL = "gemini-3.5-flash-lite"   


def get_llm(temperature: float = 0):
    return ChatGoogleGenerativeAI(model=LLM_MODEL, temperature=temperature)


def safe_invoke(chain, inputs, retries: int = 3, wait: int = 20):
    """chain.invoke with a wait-and-retry when Gemini free tier says 429."""
    for _ in range(retries):
        try:
            return chain.invoke(inputs)
        except Exception as e:  # noqa: BLE001
            if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
                print(f"[rate limit] waiting {wait}s ...")
                time.sleep(wait)
            else:
                raise
    raise RuntimeError("Gemini rate limit kept failing - try again in a minute")
