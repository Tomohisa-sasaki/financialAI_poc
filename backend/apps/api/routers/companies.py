
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from core.config import get_settings
from services.company_service import search_companies

router = APIRouter(tags=["companies"])
security = HTTPBasic()


def _auth(creds: HTTPBasicCredentials = Depends(security)):
    s = get_settings()
    if creds.username != s.API_USER or creds.password != s.API_PASSWORD:
        raise HTTPException(status_code=401, detail="Unauthorized", headers={"WWW-Authenticate": "Basic"})


@router.get("/companies/search")
def companies_search(q: str, _: str = Depends(_auth)):
    try:
        return search_companies(q)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"company search failed: {e}")
