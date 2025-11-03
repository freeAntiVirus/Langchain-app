# schemas.py
from pydantic import BaseModel
from typing import List, Optional

class GenerateFromTopicsRequest(BaseModel):
    topics: List[str]                 # chosen topic names (exact)
    exemplar_count: int = 5           # how many exemplars to feed to GPT (1..10)
    temperature: float = 0.5          # model temperature (0.2–0.7 usually fine)
    subject: str

class GenerateFromTopicsResponse(BaseModel):
    topics: List[str]
    exemplars_used: int
    latex: str                        # MathJax/KaTeX-ready LaTeX
    exemplar_ids: List[int]           # QuestionId list (for traceability)