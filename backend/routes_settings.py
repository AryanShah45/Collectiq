"""Application settings & roster.

Holds the two company display names (default "MBS" / "MCORP") and the standing
roster of collection representatives, marketing representatives and branches.
The roster drives the data-entry form: new weekly entries pre-fill a row for
each name here, so users only type numbers.

Stored as a single document (id="app") in the `settings` collection.
"""
from datetime import datetime, timezone
from typing import List

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from db import db
from auth import get_current_user, require_admin

settings_router = APIRouter(prefix="/api", tags=["settings"])

SETTINGS_ID = "app"

DEFAULTS = {
    "id": SETTINGS_ID,
    "company_a": "MBS",
    "company_b": "MCORP",
    "collection_reps": [],
    "marketing_reps": [],
    "branches": [],
}


def _clean(doc: dict) -> dict:
    doc.pop("_id", None)
    return doc


def _dedupe(names) -> List[str]:
    """Trim, drop blanks, and remove case-insensitive duplicates (keep order)."""
    seen, out = set(), []
    for n in names or []:
        n = (n or "").strip()
        if not n:
            continue
        key = n.lower()
        if key not in seen:
            seen.add(key)
            out.append(n)
    return out


class SettingsIn(BaseModel):
    company_a: str = "MBS"
    company_b: str = "MCORP"
    collection_reps: List[str] = Field(default_factory=list)
    marketing_reps: List[str] = Field(default_factory=list)
    branches: List[str] = Field(default_factory=list)


async def get_settings_doc() -> dict:
    doc = await db.settings.find_one({"id": SETTINGS_ID})
    if not doc:
        doc = dict(DEFAULTS)
        doc["updated_at"] = datetime.now(timezone.utc).isoformat()
        await db.settings.insert_one(dict(doc))
    return _clean(doc)


async def seed_settings():
    """Create the default settings document on first run (idempotent)."""
    if not await db.settings.find_one({"id": SETTINGS_ID}):
        doc = dict(DEFAULTS)
        doc["updated_at"] = datetime.now(timezone.utc).isoformat()
        await db.settings.insert_one(doc)


@settings_router.get("/settings")
async def read_settings(_: dict = Depends(get_current_user)):
    # Any logged-in user can read settings (needed for company labels, etc.)
    return await get_settings_doc()


@settings_router.put("/settings")
async def write_settings(body: SettingsIn, _: dict = Depends(require_admin)):
    update = {
        "company_a": (body.company_a or "MBS").strip() or "MBS",
        "company_b": (body.company_b or "MCORP").strip() or "MCORP",
        "collection_reps": _dedupe(body.collection_reps),
        "marketing_reps": _dedupe(body.marketing_reps),
        "branches": _dedupe(body.branches),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.settings.update_one({"id": SETTINGS_ID}, {"$set": update}, upsert=True)
    update["id"] = SETTINGS_ID
    return update


# ---------- backup & restore (a portable copy of everything) ----------
from fastapi import Body
from fastapi.responses import JSONResponse


@settings_router.get("/backup")
async def backup(_: dict = Depends(require_admin)):
    settings = await get_settings_doc()
    meetings = await db.meetings.find({}, {"_id": 0}).sort("meeting_date", 1).to_list(2000)
    payload = {
        "app": "CollectIQ",
        "version": 1,
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "settings": settings,
        "meetings": meetings,
    }
    headers = {"Content-Disposition": 'attachment; filename="collectiq-backup.json"'}
    return JSONResponse(content=payload, headers=headers)


@settings_router.post("/restore")
async def restore(payload: dict = Body(...), _: dict = Depends(require_admin)):
    if payload.get("app") != "CollectIQ":
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail="This file is not a CollectIQ backup.")
    meetings = payload.get("meetings") or []
    settings = payload.get("settings")
    await db.meetings.delete_many({})
    if meetings:
        for m in meetings:
            m.pop("_id", None)
        await db.meetings.insert_many(meetings)
    if settings:
        settings.pop("_id", None)
        settings["id"] = SETTINGS_ID
        await db.settings.update_one({"id": SETTINGS_ID}, {"$set": settings}, upsert=True)
    return {"ok": True, "restored_meetings": len(meetings)}
