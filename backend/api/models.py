from pydantic import BaseModel

class IndexRequest(BaseModel):
    source: str


class AskRequest(BaseModel):
    question: str