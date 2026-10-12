from src.parsing.loader import load_docs, chunk_docs
from src.parsing.resume_parser import parse_resume

path = r"data\resumes\my_resume.pdf"

docs = load_docs(path)
print("\nTotal number of pages:", len(docs))
print("Total number of chunks:", len(chunk_docs(docs)))

profile = parse_resume(path)
print("\nName:", profile.name)
print("\nSkills:", profile.skills)
print("\nEducation:", profile.education)
print("\nExperience:", profile.experience)
print("\nTarget role:", profile.target_role)