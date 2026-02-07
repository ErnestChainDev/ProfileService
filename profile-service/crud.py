from sqlalchemy.orm import Session
from typing import Any

from .models import UserProfile


def get_profile(db: Session, user_id: int) -> UserProfile | None:
    return (
        db.query(UserProfile)
        .filter(UserProfile.user_id == user_id)
        .first()
    )


def create_profile(db: Session, user_id: int, payload: dict[str, Any]) -> UserProfile:
    p = UserProfile(user_id=user_id)

    for field, value in payload.items():
        if hasattr(p, field):
            setattr(p, field, value)

    db.add(p)
    db.commit()
    db.refresh(p)
    return p


def update_profile(db: Session, user_id: int, payload: dict[str, Any]) -> UserProfile:
    """
    Update ONLY the current user's profile.
    Fields not provided remain unchanged.
    """
    p = get_profile(db, user_id)

    if not p:
        return create_profile(db, user_id, payload)

    for field, value in payload.items():
        if hasattr(p, field):
            setattr(p, field, value)

    db.commit()
    db.refresh(p)
    return p


def upsert_profile(db: Session, user_id: int, payload: dict[str, Any]) -> UserProfile:
    """
    Safe upsert used by GET /me bootstrap and PUT /me
    """
    p = get_profile(db, user_id)

    if not p:
        return create_profile(db, user_id, payload)

    for field, value in payload.items():
        if hasattr(p, field):
            setattr(p, field, value)

    db.commit()
    db.refresh(p)
    return p
