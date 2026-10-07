from pathlib import Path
from langchain_community.document_loaders import PyPDFLoader, Docx2txtLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter

from src.config import CHUNK_SIZE, CHUNK_OVERLAP


def load_docs(path):
    path = Path(path)
    suffix = path.suffix.lower()

    if suffix == ".pdf":
        docs = PyPDFLoader(str(path)).load()
    elif suffix == ".docx":
        docs = Docx2txtLoader(str(path)).load()
    else:
        raise ValueError(f"Unsupported file type: {suffix}. Use PDF or DOCX.")

    if not "".join(d.page_content for d in docs).strip():
        raise ValueError("No text found. The file may be a scanned image.")
    return docs


def load_resume(path) -> str:
    docs = load_docs(path)
    return "\n".join(d.page_content for d in docs).strip()


def chunk_docs(docs, size=CHUNK_SIZE, overlap=CHUNK_OVERLAP):
    splitter = RecursiveCharacterTextSplitter(chunk_size=size, chunk_overlap=overlap)
    return splitter.split_documents(docs)


if __name__ == "__main__":
    pdf_path = r"data\resumes\my_resume.pdf"
    docs = load_docs(pdf_path)
    print("\nUploaded file name:", Path(pdf_path).name)
    print("\nTotal number of pages:", len(docs))
    print("\nTotal number of characters:", sum(len(d.page_content) for d in docs))
    chunks = chunk_docs(docs)
    print("\nTotal number of chunks created:", len(chunks))