import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List
from app.database import get_db
from app import models, schemas

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/sources", tags=["sources"])


def _with_count(source: models.Source, db: Session) -> schemas.SourceResponse:
    count = db.query(func.count(models.Event.id)).filter(models.Event.source_id == source.id).scalar() or 0
    resp = schemas.SourceResponse.model_validate(source)
    resp.events_count = count
    return resp


@router.get("", response_model=List[schemas.SourceResponse])
async def list_sources(db: Session = Depends(get_db)):
    sources = db.query(models.Source).order_by(models.Source.name).all()
    return [_with_count(s, db) for s in sources]


@router.post("", response_model=schemas.SourceResponse, status_code=201)
async def create_source(source: schemas.SourceInput, db: Session = Depends(get_db)):
    existing = db.query(models.Source).filter(models.Source.url == source.url).first()
    if existing:
        raise HTTPException(status_code=409, detail="Source with this URL already exists")
    db_source = models.Source(**source.model_dump())
    db.add(db_source)
    db.commit()
    db.refresh(db_source)
    return _with_count(db_source, db)


@router.put("/{source_id}", response_model=schemas.SourceResponse)
async def update_source(source_id: int, update: schemas.SourceUpdate, db: Session = Depends(get_db)):
    source = db.query(models.Source).filter(models.Source.id == source_id).first()
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")
    for k, v in update.model_dump(exclude_none=True).items():
        setattr(source, k, v)
    db.commit()
    db.refresh(source)
    return _with_count(source, db)


@router.delete("/{source_id}", status_code=204)
async def delete_source(source_id: int, db: Session = Depends(get_db)):
    source = db.query(models.Source).filter(models.Source.id == source_id).first()
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")
    db.delete(source)
    db.commit()
