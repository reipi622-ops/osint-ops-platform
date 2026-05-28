import logging
from fastapi import APIRouter
from app import schemas
from app.services.pattern_engine import get_active_patterns

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/patterns", tags=["patterns"])


@router.get("", response_model=schemas.PatternListResponse)
async def list_patterns():
    """Return all active (non-expired) intelligence patterns."""
    patterns_raw = get_active_patterns()
    items = [schemas.PatternAlert(**p) for p in patterns_raw]
    return schemas.PatternListResponse(patterns=items, total=len(items))
