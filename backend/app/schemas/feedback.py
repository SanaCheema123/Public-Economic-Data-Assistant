from pydantic import BaseModel, Field

class FeedbackRequest(BaseModel):
    query_result_id: str
    rating: str = Field(pattern="^(helpful|not_helpful)$")
