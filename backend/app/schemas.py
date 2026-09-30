from pydantic import BaseModel, Field

class LoginRequest(BaseModel):
    username: str
    password: str

class ChatRequest(BaseModel):
    question: str = Field(min_length=1, max_length=4000)

class Source(BaseModel):
    source_document: str
    section_title: str
    collection: str

class ChatResponse(BaseModel):
    answer: str
    sources: list[Source]
    retrieval_type: str
    role: str
