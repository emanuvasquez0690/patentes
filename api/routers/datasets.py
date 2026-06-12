from fastapi import APIRouter, HTTPException, Query

from api.schemas.responses import DatasetDataResponse, DatasetPreviewResponse
from api.services.dataset_service import get_dataset_info, get_dataset_preview, get_dataset_records


router = APIRouter(prefix="/datasets", tags=["datasets"])


@router.get("/{dataset_id}")
def read_dataset_info(dataset_id: str) -> dict:
    dataset = get_dataset_info(dataset_id)
    if dataset is None:
        raise HTTPException(status_code=404, detail="Dataset not found")
    return dataset


@router.get("/{dataset_id}/preview", response_model=DatasetPreviewResponse)
def read_dataset_preview(dataset_id: str, limit: int = Query(default=50, ge=1, le=500)) -> DatasetPreviewResponse:
    preview_df = get_dataset_preview(dataset_id, limit=limit)
    if preview_df.empty:
        raise HTTPException(status_code=404, detail="Preview unavailable")
    return DatasetPreviewResponse(dataset_id=dataset_id, total=len(preview_df), items=preview_df.to_dict(orient="records"))


@router.get("/{dataset_id}/data", response_model=DatasetDataResponse)
def read_dataset_data(
    dataset_id: str,
    limit: int = Query(default=200, ge=1, le=5000),
    offset: int = Query(default=0, ge=0),
) -> DatasetDataResponse:
    data_df = get_dataset_records(dataset_id=dataset_id, limit=limit, offset=offset)
    if data_df.empty:
        raise HTTPException(status_code=404, detail="Dataset data unavailable")
    return DatasetDataResponse(dataset_id=dataset_id, total=len(data_df), items=data_df.to_dict(orient="records"))
