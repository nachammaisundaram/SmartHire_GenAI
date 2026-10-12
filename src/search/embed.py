from langchain_google_genai import GoogleGenerativeAIEmbeddings

from src.config import EMBED_MODEL

embeddings = GoogleGenerativeAIEmbeddings(model=EMBED_MODEL)