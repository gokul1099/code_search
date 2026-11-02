from pydantic import BaseModel

class IndexRequest(BaseModel):
    source: str