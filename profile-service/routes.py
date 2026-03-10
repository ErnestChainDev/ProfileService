from __future__ import annotations

import os
from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.orm import Session

from shared.database import db_dependency
from shared.utils import decode_token

from .schemas import ProfileUpsertIn, ProfileOut
from .crud import get_profile, upsert_profile

router = APIRouter()


def build_router(SessionLocal):
    get_db = db_dependency(SessionLocal)
    JWT_SECRET = os.getenv("JWT_SECRET", "")
    JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
    SERVICE_TOKEN = os.getenv("SERVICE_TOKEN", "")

    if not JWT_SECRET:
        raise RuntimeError("JWT_SECRET not configured")
    if not SERVICE_TOKEN:
        raise RuntimeError("SERVICE_TOKEN not configured")

    def current_user_id(
        authorization: str | None = Header(default=None),
        x_user_id: str | None = Header(default=None, alias="X-User-ID"),
    ) -> int:
        if authorization and authorization.lower().startswith("bearer "):
            token = authorization.split(" ", 1)[1].strip()
            try:
                data = decode_token(token, JWT_SECRET, JWT_ALGORITHM)
                sub = data.get("sub")
                if not sub:
                    raise HTTPException(status_code=401, detail="Token missing sub")
                uid = int(sub)
                if uid <= 0:
                    raise HTTPException(status_code=401, detail="Invalid user id")
                return uid
            except Exception:
                raise HTTPException(status_code=401, detail="Invalid token")

        if not x_user_id:
            raise HTTPException(status_code=401, detail="Missing Authorization or X-User-ID")

        try:
            uid = int(x_user_id)
        except ValueError:
            raise HTTPException(status_code=401, detail="Invalid X-User-ID")

        if uid <= 0:
            raise HTTPException(status_code=401, detail="Invalid user id")
        return uid

    def ensure_service_access(x_service_token: str | None) -> None:
        if not SERVICE_TOKEN:
            raise HTTPException(status_code=500, detail="SERVICE_TOKEN not configured")
        if x_service_token != SERVICE_TOKEN:
            raise HTTPException(status_code=403, detail="Forbidden")

    def to_profile_out(user_id: int, p) -> ProfileOut:
        return ProfileOut(
            user_id=user_id,
            full_name=p.full_name or "",
            year_level=p.year_level or "",
            bio=p.bio or "",
            interests=p.interests or "",
            career_goals=p.career_goals or "",
            preferred_program=p.preferred_program or "",
            skills=p.skills or "",
            notes=p.notes or "",
        )

    def _ensure_profile(db: Session, user_id: int, payload: dict | None = None):
        return upsert_profile(db, user_id, payload or {})

    @router.get("/me", response_model=ProfileOut)
    def me(uid: int = Depends(current_user_id), db: Session = Depends(get_db)):
        p = get_profile(db, uid)
        if not p:
            p = _ensure_profile(db, uid)
        return to_profile_out(uid, p)

    @router.put("/me", response_model=ProfileOut)
    def update_me(
        payload: ProfileUpsertIn,
        uid: int = Depends(current_user_id),
        db: Session = Depends(get_db),
    ):
        data = payload.model_dump(exclude_unset=True)
        p = upsert_profile(db, uid, data)
        return to_profile_out(uid, p)

    @router.post("/internal/bootstrap", response_model=ProfileOut)
    def bootstrap(
        user_id: int,
        email: str,
        full_name: str = "",
        x_service_token: str | None = Header(default=None, alias="X-Service-Token"),
        db: Session = Depends(get_db),
    ):
        ensure_service_access(x_service_token)

        name = full_name.strip() if full_name else (email.split("@")[0] if email else "")
        p = get_profile(db, user_id)
        if not p:
            p = _ensure_profile(db, user_id, {"full_name": name})
        else:
            if (p.full_name or "").strip() == "" and name:
                p = upsert_profile(db, user_id, {"full_name": name})

        return to_profile_out(user_id, p)

    # ✅ INTERNAL: used by recommendation-service
    @router.get("/by-user/{user_id}", response_model=ProfileOut)
    def get_by_user(
        user_id: int,
        x_service_token: str | None = Header(default=None, alias="X-Service-Token"),
        db: Session = Depends(get_db),
    ):
        ensure_service_access(x_service_token)

        p = get_profile(db, user_id)
        if not p:
            p = _ensure_profile(db, user_id)

        return to_profile_out(user_id, p)

    return router