
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from core.config import get_settings
from analysis.report import build_pdf
from services.email_service import send_pdf_via_email
import io
import re

router = APIRouter(tags=["report"])
security = HTTPBasic()


def _auth(creds: HTTPBasicCredentials = Depends(security)):
    s = get_settings()
    if creds.username != s.API_USER or creds.password != s.API_PASSWORD:
        raise HTTPException(status_code=401, detail="Unauthorized", headers={"WWW-Authenticate": "Basic"})


class PDFPayload(BaseModel):
    title: str = Field("Report")
    companies: List[Dict[str, Any]] = Field(default_factory=list)
    metrics: List[str] = Field(default_factory=list)
    charts: List[str] = Field(default_factory=list, description="Base64 images, can be data URLs or raw base64")
    scenario: Optional[Dict[str, Any]] = None


class EmailPayload(PDFPayload):
    to: str = Field(..., description="recipient email address")
    subject: str = Field("Financial Report")
    text: str = Field("See attached report.")


def _sanitize_filename(s: str) -> str:
    s = s.strip() or "report"
    s = re.sub(r"[^A-Za-z0-9._-]", "_", s)
    return s[:80]


@router.post("/report/pdf")
def generate_pdf(data: PDFPayload, _: str = Depends(_auth)):
    try:
        pdf = build_pdf(data.title, data.companies, data.metrics, data.charts, data.scenario)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"pdf generation failed: {e}")

    filename = _sanitize_filename(data.title or "report") + ".pdf"
    return StreamingResponse(io.BytesIO(pdf), media_type="application/pdf", headers={
        "Content-Disposition": f"attachment; filename={filename}"
    })


@router.post("/report/email")
def email_pdf(data: EmailPayload, _: str = Depends(_auth)):
    try:
        pdf = build_pdf(data.title, data.companies, data.metrics, data.charts, data.scenario)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"pdf generation failed: {e}")

    ok = send_pdf_via_email(data.to, data.subject, data.text, pdf)
    if not ok:
        raise HTTPException(status_code=500, detail="email failed")
    return {"status": "sent", "to": data.to}
