from fastapi import APIRouter, HTTPException, Query

from api.schemas.responses import CatalogueResponse
from api.services.catalogue_service import get_catalogue, search_catalogue


router = APIRouter(prefix="/catalogue", tags=["catalogue"])


@router.get("", response_model=CatalogueResponse)
def read_catalogue(query: str | None = Query(default=None), tag: str | None = Query(default=None)) -> CatalogueResponse:
    catalogue_df = get_catalogue()
    if catalogue_df.empty:
        raise HTTPException(status_code=404, detail="No catalogue available")

    tags = [tag] if tag else []
    filtered_df = search_catalogue(catalogue_df, query=query or "", selected_tags=tags)
    return CatalogueResponse(items=filtered_df.to_dict(orient="records"), total=len(filtered_df))
