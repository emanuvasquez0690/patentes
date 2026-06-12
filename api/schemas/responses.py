from typing import Any

from pydantic import BaseModel, Field


class CatalogueResponse(BaseModel):
    items: list[dict[str, Any]] = Field(default_factory=list)
    total: int


class DatasetPreviewResponse(BaseModel):
    dataset_id: str
    total: int
    items: list[dict[str, Any]] = Field(default_factory=list)


class DatasetDataResponse(BaseModel):
    dataset_id: str
    total: int
    items: list[dict[str, Any]] = Field(default_factory=list)


class ChartResponse(BaseModel):
    dataset_id: str
    chart_type: str
    mime_type: str = "image/png"
    image_base64: str
