from pydantic import BaseModel

class FakeJobRequest(BaseModel):
    repo_id: str
    steps: int = 10
    fail: bool = False
