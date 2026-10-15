from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    question: str = Field(min_length=2, max_length=4000)
    chat_session_id: str | None = None
    language: str | None = Field(default=None, pattern="^(en|ar)$")


class QueryValidationRequest(BaseModel):
    sql: str = Field(min_length=1, max_length=10000)
    params: dict = Field(default_factory=dict)


class QueryRequest(BaseModel):
    question: str = Field(min_length=2, max_length=4000)
    language: str | None = Field(default=None, pattern="^(en|ar)$")
