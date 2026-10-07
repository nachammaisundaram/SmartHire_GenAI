import sys

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.exceptions import OutputParserException
from pydantic import BaseModel, Field

from src.config import GEMINI_API_KEY, LLM_MODEL, MAX_RETRIES
from src.parsing.loader import load_resume


class Experience(BaseModel):
    role: str = ""
    company: str = ""
    duration: str = ""
    highlights: list[str] = Field(default_factory=list)


class Education(BaseModel):
    degree: str = ""
    institution: str = ""
    year: str = ""


class ResumeProfile(BaseModel):
    name: str
    email: str = ""
    skills: list[str] = Field(default_factory=list)
    experience: list[Experience] = Field(default_factory=list)
    education: list[Education] = Field(default_factory=list)
    target_role: str = ""
    summary: str = ""



if not GEMINI_API_KEY:
    raise RuntimeError("GEMINI_API_KEY missing. Add it to your .env file.")

output_parser = PydanticOutputParser(pydantic_object=ResumeProfile)

llm = ChatGoogleGenerativeAI(
    model=LLM_MODEL,
    temperature=0,
    google_api_key=GEMINI_API_KEY,
)

prompt = ChatPromptTemplate.from_messages([
    (
        "system",
        """You are a resume parser. Read the resume text and extract the candidate's details.
        Use only the information present in the resume. Never guess or invent anything.
        If a field is missing in the resume, leave it empty ("" or []).
        For target_role, give the role the candidate is aiming for (from the objective or summary), else "".

        {format_instructions}"""
    ),
    (
        "human",
        "Resume text:\n{resume_text}"
    ),
]).partial(format_instructions=output_parser.get_format_instructions())

parser_chain = prompt | llm | output_parser


def parse_resume_text(resume_text: str) -> ResumeProfile:
    last_error = None
    for attempt in range(MAX_RETRIES + 1):
        try:
            return parser_chain.invoke({"resume_text": resume_text})
        except OutputParserException as e:
            last_error = e
            print(f"Attempt {attempt + 1} failed: {e}")
    raise ValueError(f"Could not parse resume after retries: {last_error}")


def parse_resume(path) -> ResumeProfile:
    return parse_resume_text(load_resume(path))


if __name__ == "__main__":
    # python -m src.parsing.resume_parser data\resumes\my_resume.pdf
    profile = parse_resume(sys.argv[1])
    print(profile.model_dump_json(indent=2))