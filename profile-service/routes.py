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

    # -------------------------------------------------
    # Auth: allow BOTH styles
    # 1) Authorization: Bearer <jwt> (frontend-direct)
    # 2) X-User-ID header (gateway-forwarded)
    # -------------------------------------------------
    def current_user_id(
        authorization: str | None = Header(default=None),
        x_user_id: str | None = Header(default=None, alias="X-User-ID"),
    ) -> int:
        # ✅ Preferred: JWT
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

        # ✅ Fallback: gateway header
        if not x_user_id:
            raise HTTPException(status_code=401, detail="Missing Authorization or X-User-ID")

        try:
            uid = int(x_user_id)
        except ValueError:
            raise HTTPException(status_code=401, detail="Invalid X-User-ID")

        if uid <= 0:
            raise HTTPException(status_code=401, detail="Invalid user id")
        return uid

    def _ensure_profile(db: Session, user_id: int, payload: dict | None = None):
        base = {
            "full_name": "",
            "year_level": "",
            "bio": "",
            "interests": "",
            "career_goals": "",
            "preferred_program": "",
            "skills": "",
            "notes": "",
        }
        if payload:
            base.update(payload)
        return upsert_profile(db, user_id, base)

    # -------------------------------------------------
    # PUBLIC: Get my profile (auto-create if missing)
    # -------------------------------------------------
    @router.get("/me", response_model=ProfileOut)
    def me(uid: int = Depends(current_user_id), db: Session = Depends(get_db)):
        p = get_profile(db, uid)
        if not p:
            p = _ensure_profile(db, uid)

        return ProfileOut(
            user_id=uid,
            full_name=p.full_name or "",
            year_level=p.year_level or "",
            bio=p.bio or "",
            interests=p.interests or "",
            career_goals=p.career_goals or "",
            preferred_program=p.preferred_program or "",
            skills=p.skills or "",
            notes=p.notes or "",
        )

    # -------------------------------------------------
    # PUBLIC: Update my profile
    # -------------------------------------------------
    @router.put("/me", response_model=ProfileOut)
    def update_me(
        payload: ProfileUpsertIn,
        uid: int = Depends(current_user_id),
        db: Session = Depends(get_db),
    ):
        data = payload.model_dump(exclude_unset=True)

        p = upsert_profile(db, uid, data)
        return ProfileOut(
            user_id=uid,
            full_name=p.full_name or "",
            year_level=p.year_level or "",
            bio=p.bio or "",
            interests=p.interests or "",
            career_goals=p.career_goals or "",
            preferred_program=p.preferred_program or "",
            skills=p.skills or "",
            notes=p.notes or "",
        )

    # -------------------------------------------------
    # INTERNAL: Bootstrap Profile (called by auth-service)
    # Idempotent: safe tawagin kahit paulit-ulit
    # -------------------------------------------------
    @router.post("/internal/bootstrap", response_model=ProfileOut)
    def bootstrap(
        user_id: int,
        email: str,
        full_name: str = "",
        x_service_token: str | None = Header(default=None, alias="X-Service-Token"),
        db: Session = Depends(get_db),
    ):
        if not SERVICE_TOKEN:
            raise HTTPException(status_code=500, detail="SERVICE_TOKEN not configured")
        if x_service_token != SERVICE_TOKEN:
            raise HTTPException(status_code=403, detail="Forbidden")

        # Default full_name if empty: use email prefix
        name = full_name.strip() if full_name else (email.split("@")[0] if email else "")
        p = get_profile(db, user_id)
        if not p:
            p = _ensure_profile(db, user_id, {"full_name": name})
        else:
            # only fill if blank
            if (p.full_name or "").strip() == "" and name:
                p = upsert_profile(db, user_id, {"full_name": name})

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

    return router