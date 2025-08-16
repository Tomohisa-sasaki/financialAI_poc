
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from pydantic import BaseModel, Field
from typing import Optional
from core.config import get_settings

router = APIRouter(tags=["ai"])
security = HTTPBasic()


def _auth(creds: HTTPBasicCredentials = Depends(security)):
    s = get_settings()
    if creds.username != s.API_USER or creds.password != s.API_PASSWORD:
        raise HTTPException(status_code=401, detail="Unauthorized", headers={"WWW-Authenticate": "Basic"})


class AskBody(BaseModel):
    question: str = Field(..., min_length=1)
    system: Optional[str] = Field(None, description="Optional system prompt")


@router.post("/ai/ask")
def ask_ai(body: AskBody, _: str = Depends(_auth)):
    # Placeholder: integrate your LLM provider here (OpenAI, Azure, etc.)
    # Keep the API stable so the frontend can rely on it.
    q = body.question.strip()
    if not q:
        raise HTTPException(status_code=400, detail="question is required")
    return {"answer": f"(Demo) You asked: {q}"}
