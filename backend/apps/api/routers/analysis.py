
from fastapi import APIRouter, Response, Depends, HTTPException
from pydantic import BaseModel, Field, field_validator
from typing import Dict, List, Optional
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from core.config import get_settings
from services.metrics_service import calc_metrics
from services.financial_service import get_financials
from analysis.visualizer import line_chart_image

router = APIRouter(prefix="/analysis", tags=["analysis"])
security = HTTPBasic()


def _auth(creds: HTTPBasicCredentials = Depends(security)):
    s = get_settings()
    if creds.username != s.API_USER or creds.password != s.API_PASSWORD:
        raise HTTPException(status_code=401, detail="Unauthorized", headers={"WWW-Authenticate": "Basic"})


class TimeseriesBody(BaseModel):
    companyIds: List[str] = Field(..., min_length=1)
    metricIds: List[str] = Field(..., min_length=1)
    period: str = Field("fy", description="fy | q | tq (backend dependent)")

    @field_validator("period")
    @classmethod
    def _validate_period(cls, v: str) -> str:
        allowed = {"fy", "q", "tq"}
        if v not in allowed:
            raise ValueError(f"period must be one of {sorted(allowed)}")
        return v


@router.post("/timeseries")
def timeseries(body: TimeseriesBody, _: str = Depends(_auth)):
    # Opportunistic preload of financials into cache/DB for each company
    for cid in body.companyIds:
        try:
            get_financials(cid, period=body.period)
        except Exception:
            # Non-fatal: calc_metrics may still succeed using cached/available data
            pass
    try:
        # NOTE: calc_metrics is expected to return decimals (e.g., 0.123 for 12.3%)
        return calc_metrics(body.companyIds, body.metricIds, period=body.period)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"metrics calculation failed: {e}")


class ChartBody(BaseModel):
    # { label: {period: value} }
    series: Dict[str, Dict[str, Optional[float]]]
    title: str = ""
    ylabel: str = ""
    yformat: Optional[str] = Field(None, description="percent | percent100 | thousands | None")
    rotate_xticks: Optional[int] = Field(None, description="Rotation degrees for x tick labels")

    @field_validator("yformat")
    @classmethod
    def _validate_yformat(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        allowed = {"percent", "percent100", "thousands"}
        if v not in allowed:
            raise ValueError(f"yformat must be one of {sorted(allowed)}")
        return v


@router.post("/chart.png")
def chart_png(body: ChartBody, _: str = Depends(_auth)):
    # Convert nested dict into the visualizer-friendly list of tuples
    try:
        series_map = {
            label: [(k, v) for k, v in kv.items()]  # ordering handled in visualizer via natural sort
            for label, kv in body.series.items()
        }
        img = line_chart_image(
            series_map,
            title=body.title,
            ylabel=body.ylabel,
            yformat=body.yformat,
            rotate_xticks=body.rotate_xticks,
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"chart rendering failed: {e}")
    return Response(content=img, media_type="image/png")
