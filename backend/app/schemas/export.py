from pydantic import BaseModel


class ExportRequest(BaseModel):
    query_result_id: str
    language: str = "en"
