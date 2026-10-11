# SmartHire Evaluation Report

## 1. Retrieval hit rate (top-3)

**Job search: 5/5 = 100%**

| query | expected keyword | rank found |
|---|---|---|
| docker jenkins ci cd pipeline | devops | 1 |
| python machine learning model training | machine learning | 1 |
| langchain rag chatbot llm | gen | 1 |
| sql dashboards power bi | data | 1 |
| react node full stack web app | full | 1 |

**Career KB: 3/5 = 60%**

| query | expected keyword | rank found |
|---|---|---|
| What should a fresher learn first for Gen AI? | fresher | miss |
| How do I prepare for a RAG interview? | rag | 1 |
| What is SmartHire? | smarthire | 1 |
| Should I do a Ph.D. after MCA? | ph | miss |
| How to show DevOps experience in a Gen AI resume? | devops | 1 |

## 2. Mentor answer quality (LLM judge, 1-5)

| question | relevance | groundedness | actionability | comment |
|---|---|---|---|---|
| What should I learn first to become a Gen AI  | 5 | 5 | 5 | The answer directly addresses what to learn first, is fully grounded i |
| How do I explain my DevOps internship in a Ge | 3 | 3 | 3 | The context mentions moving from DevOps to AI and highlights MLOps and |
| What projects should a fresher put on a Gen A | 5 | 5 | 5 | The answer directly lists the recommended projects from the context, s |
| How do I prepare for UGC NET while working? | 5 | 5 | 4 | The answer directly addresses the question using the provided context, |

**Average: relevance 4.5, groundedness 4.5, actionability 4.25**

## 3. Prompt before / after (cv_suggest v1 vs v2, 5 resumes, 1-5)

| criterion | v1 (before) | v2 (after) |
|---|---|---|
| specificity | 4.8 | 4.6 |
| grounded | 3.4 | 5.0 |
| actionable | 4.6 | 5.0 |
| structure | 4.8 | 5.0 |

## 4. Hallucination checks

**(a) Rewrite my resume: invented numbers/skills after the guard**

| resume | needed fix pass | still-new items |
|---|---|---|
| My_Resume.pdf | no | none |
| Sample_DataAnalyst.pdf | no | none |
| Sample_DevOps.pdf | no | none |
| Sample_FullStack.pdf | no | none |
| Sample_GenAI.pdf | yes | none |

**(b) Out-of-KB questions: mentor admitted it does not know 3/3**

| question | admitted not knowing | answer start |
|---|---|---|
| What is the exact salary of a Gen AI intern at Zoho? | yes | I do not have enough information in your knowledge base to answer that. Salary v |
| Who won the cricket world cup in 2011? | yes | That is outside career guidance, but I would be happy to help you with a related |
| Which company will definitely hire me next month? | yes | I cannot answer that question because it is outside career guidance, and I can n |
