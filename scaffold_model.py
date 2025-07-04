from pydantic import BaseModel
from typing import List, Optional

class PulseScaffold(BaseModel):
    title: str
    summary: str
    tone: str
    keywords: List[str]
    resonance: float
    coherence: float
    source_url: Optional[str] = None

class Source(BaseModel):
    name: str
    url: str
    tone: str

class Glyph(BaseModel):
    symbol: str
    meaning: str
    tone: str

