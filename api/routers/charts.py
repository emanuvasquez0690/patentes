from fastapi import APIRouter, HTTPException, Query

from api.schemas.responses import ChartResponse
from api.services.chart_service import build_dataset_chart_base64


router = APIRouter(prefix="/charts", tags=["charts"])


@router.get("/{dataset_id}", response_model=ChartResponse)
def read_chart(
    dataset_id: str,
    chart_type: str = Query(default="auto"),
    limit: int = Query(default=500, ge=1, le=5000),
) -> ChartResponse:
    result = build_dataset_chart_base64(dataset_id=dataset_id, chart_type=chart_type, limit=limit)
    if result is None:
        raise HTTPException(status_code=404, detail="Chart could not be generated")
    return result
