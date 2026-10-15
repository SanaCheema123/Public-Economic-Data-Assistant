from pydantic import BaseModel, Field


class SaveItemRequest(BaseModel):
    query_result_id: str | None = None
    collection_id: str | None = None
    item_type: str = Field(default="answer", pattern="^(answer|chart|report|research)$")
    title: str = Field(min_length=1, max_length=300)
    description: str | None = Field(default=None, max_length=2000)
    payload: dict = Field(default_factory=dict)


class CollectionCreate(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    description: str | None = Field(default=None, max_length=1000)

class SavedItemUpdate(BaseModel):
    collection_id: str | None = None
    title: str | None = Field(default=None, min_length=1, max_length=300)
