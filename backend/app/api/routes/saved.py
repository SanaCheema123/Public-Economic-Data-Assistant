from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import asc, desc, or_, select
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.models.entities import Collection, Query as UserQuery, QueryResult, SavedItem, User
from app.schemas.saved import CollectionCreate, SaveItemRequest, SavedItemUpdate
from app.security.dependencies import get_current_user

router = APIRouter(prefix="/api", tags=["Saved items"])


def _result_owned_by_user(db: Session, result_id: str, user_id: str) -> bool:
    return bool(db.scalar(
        select(QueryResult.id)
        .join(UserQuery, UserQuery.id == QueryResult.query_id)
        .where(QueryResult.id == result_id, UserQuery.user_id == user_id)
    ))


@router.get("/saved")
def list_saved(
    q: str | None = None,
    item_type: str | None = None,
    collection_id: str | None = None,
    sort: str = Query(default="recent", pattern="^(recent|oldest|title)$"),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    stmt = select(SavedItem).where(SavedItem.user_id == user.id)
    if q:
        pattern = f"%{q.strip()}%"
        stmt = stmt.where(or_(SavedItem.title.ilike(pattern), SavedItem.description.ilike(pattern)))
    if item_type:
        stmt = stmt.where(SavedItem.item_type == item_type)
    if collection_id:
        stmt = stmt.where(SavedItem.collection_id == collection_id)
    if sort == "oldest":
        stmt = stmt.order_by(asc(SavedItem.created_at))
    elif sort == "title":
        stmt = stmt.order_by(asc(SavedItem.title))
    else:
        stmt = stmt.order_by(desc(SavedItem.created_at))
    items = db.scalars(stmt).all()
    collections = db.scalars(select(Collection).where(Collection.user_id == user.id).order_by(Collection.name)).all()
    return {
        "items": [{
            "id": x.id, "query_result_id": x.query_result_id, "collection_id": x.collection_id,
            "item_type": x.item_type, "title": x.title, "description": x.description,
            "payload": x.payload_json, "created_at": x.created_at.isoformat(), "updated_at": x.updated_at.isoformat(),
        } for x in items],
        "collections": [{"id": c.id, "name": c.name, "description": c.description, "created_at": c.created_at.isoformat()} for c in collections],
    }


@router.post("/saved", status_code=201)
def save_item(payload: SaveItemRequest, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    if payload.query_result_id and not _result_owned_by_user(db, payload.query_result_id, user.id):
        raise HTTPException(status_code=404, detail="Query result not found")
    if payload.collection_id:
        collection = db.get(Collection, payload.collection_id)
        if not collection or collection.user_id != user.id:
            raise HTTPException(status_code=404, detail="Collection not found")
    item = SavedItem(
        user_id=user.id,
        query_result_id=payload.query_result_id,
        collection_id=payload.collection_id,
        item_type=payload.item_type,
        title=payload.title,
        description=payload.description,
        payload_json=payload.payload,
    )
    db.add(item); db.commit(); db.refresh(item)
    return {"id": item.id, "message": "Saved"}


@router.patch("/saved/{item_id}")
def update_saved(item_id: str, payload: SavedItemUpdate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    item = db.get(SavedItem, item_id)
    if not item or item.user_id != user.id:
        raise HTTPException(status_code=404, detail="Saved item not found")
    if payload.collection_id:
        collection = db.get(Collection, payload.collection_id)
        if not collection or collection.user_id != user.id:
            raise HTTPException(status_code=404, detail="Collection not found")
    item.collection_id = payload.collection_id
    if payload.title is not None:
        item.title = payload.title.strip()
    db.commit()
    return {"id": item.id, "message": "Updated"}


@router.delete("/saved/{item_id}", status_code=204)
def delete_saved(item_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    item = db.get(SavedItem, item_id)
    if not item or item.user_id != user.id:
        raise HTTPException(status_code=404, detail="Saved item not found")
    db.delete(item); db.commit()
    return None


@router.post("/collections", status_code=201)
def create_collection(payload: CollectionCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    existing = db.scalar(select(Collection).where(Collection.user_id == user.id, Collection.name == payload.name))
    if existing:
        raise HTTPException(status_code=409, detail="A collection with this name already exists")
    collection = Collection(user_id=user.id, name=payload.name.strip(), description=payload.description)
    db.add(collection); db.commit(); db.refresh(collection)
    return {"id": collection.id, "name": collection.name, "description": collection.description}


@router.delete("/collections/{collection_id}", status_code=204)
def delete_collection(collection_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    collection = db.get(Collection, collection_id)
    if not collection or collection.user_id != user.id:
        raise HTTPException(status_code=404, detail="Collection not found")
    # Saved items remain but become ungrouped via FK ON DELETE SET NULL in PostgreSQL.
    db.delete(collection); db.commit()
    return None
