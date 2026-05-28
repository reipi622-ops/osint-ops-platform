import logging
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app import schemas
from app.services.geo_intel import compute_clusters, get_hotzones

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/geo", tags=["geo"])


@router.get("/clusters", response_model=schemas.GeoClusterListResponse)
async def list_clusters(db: Session = Depends(get_db)):
    """Return all geographic event clusters from the past 24 hours."""
    clusters = compute_clusters(db)
    items = [schemas.GeoCluster(**c.to_dict()) for c in clusters]
    hotzones = sum(1 for c in clusters if c.is_hotzone)
    return schemas.GeoClusterListResponse(clusters=items, total=len(items), hotzones=hotzones)


@router.get("/hotzone", response_model=schemas.GeoClusterListResponse)
async def list_hotzones(db: Session = Depends(get_db)):
    """Return only hot zones — clusters with ≥4 events in the last 24 hours."""
    zones = get_hotzones(db)
    items = [schemas.GeoCluster(**z.to_dict()) for z in zones]
    return schemas.GeoClusterListResponse(clusters=items, total=len(items), hotzones=len(items))
