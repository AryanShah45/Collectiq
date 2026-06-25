import uuid
from datetime import datetime, timezone, date
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from pydantic import BaseModel, Field

from db import db
from auth import get_current_user, require_admin
import extraction
import os
import tempfile

meetings_router = APIRouter(prefix="/api", tags=["meetings"])


# ---------- models ----------
class Amount(BaseModel):
    mbs: float = 0
    mcorp: float = 0


class Aging(BaseModel):
    d90: Amount = Field(default_factory=Amount)
    d60: Amount = Field(default_factory=Amount)
    d30: Amount = Field(default_factory=Amount)
    othera: Amount = Field(default_factory=Amount)


class Performance(BaseModel):
    purchase: Amount = Field(default_factory=Amount)
    sales: Amount = Field(default_factory=Amount)
    coll_per_day: float = 0
    coll_pct: float = 0
    new_target: float = 0
    last_week_target: float = 0


class RepEntry(BaseModel):
    name: str
    aging: Aging = Field(default_factory=Aging)
    performance: Performance = Field(default_factory=Performance)


class Quotation(BaseModel):
    prepair: Amount = Field(default_factory=Amount)
    conform: Amount = Field(default_factory=Amount)
    pending: Amount = Field(default_factory=Amount)
    under_process: Amount = Field(default_factory=Amount)
    not_conform: Amount = Field(default_factory=Amount)


class MeetingIn(BaseModel):
    title: str = "Weekly Collection Meeting"
    meeting_date: str
    period_start: str = ""
    period_end: str = ""
    notes: str = ""
    reps: List[RepEntry] = Field(default_factory=list)
    quotation: Quotation = Field(default_factory=Quotation)


# ---------- helpers ----------
def _derive_period(meeting_date: str):
    try:
        d = date.fromisoformat(meeting_date[:10])
    except Exception:
        d = datetime.now(timezone.utc).date()
    iso = d.isocalendar()
    return {
        "week_label": f"{iso[0]}-W{iso[1]:02d}",
        "month": d.month,
        "year": d.year,
    }


def _enrich(meeting: dict) -> dict:
    """Attach computed summary used by lists & trends (company = all)."""
    d90 = d60 = d30 = othera = 0.0
    total_new_target = total_last_target = total_coll_day = 0.0
    pcts = []
    for rep in meeting.get("reps", []):
        ag = rep.get("aging", {})
        for bucket, acc in (("d90", "d90"), ("d60", "d60"), ("d30", "d30"), ("othera", "othera")):
            a = ag.get(bucket, {}) or {}
            v = (a.get("mbs", 0) or 0) + (a.get("mcorp", 0) or 0)
            if acc == "d90":
                d90 += v
            elif acc == "d60":
                d60 += v
            elif acc == "d30":
                d30 += v
            else:
                othera += v
        perf = rep.get("performance", {})
        total_new_target += perf.get("new_target", 0) or 0
        total_last_target += perf.get("last_week_target", 0) or 0
        total_coll_day += perf.get("coll_per_day", 0) or 0
        if perf.get("coll_pct"):
            pcts.append(perf.get("coll_pct"))
    total_outstanding = d90 + d60 + d30 + othera
    meeting["summary"] = {
        "total_outstanding": round(total_outstanding, 2),
        "d90": round(d90, 2),
        "d60": round(d60, 2),
        "d30": round(d30, 2),
        "othera": round(othera, 2),
        "total_new_target": round(total_new_target, 2),
        "total_last_target": round(total_last_target, 2),
        "total_coll_per_day": round(total_coll_day, 2),
        "avg_coll_pct": round(sum(pcts) / len(pcts), 2) if pcts else 0,
        "rep_count": len(meeting.get("reps", [])),
    }
    return meeting


def _clean(meeting: dict) -> dict:
    meeting.pop("_id", None)
    return meeting


# ---------- routes ----------
@meetings_router.get("/meetings")
async def list_meetings(_: dict = Depends(get_current_user)):
    docs = await db.meetings.find({}, {"_id": 0}).sort("meeting_date", -1).to_list(500)
    return [_enrich(d) for d in docs]


@meetings_router.get("/meetings/{meeting_id}")
async def get_meeting(meeting_id: str, _: dict = Depends(get_current_user)):
    doc = await db.meetings.find_one({"id": meeting_id}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Meeting not found")
    return _enrich(doc)


@meetings_router.post("/meetings")
async def create_meeting(body: MeetingIn, admin: dict = Depends(require_admin)):
    now = datetime.now(timezone.utc).isoformat()
    doc = body.model_dump()
    doc.update(_derive_period(body.meeting_date))
    doc["id"] = str(uuid.uuid4())
    doc["created_by"] = admin.get("name") or admin.get("email")
    doc["created_at"] = now
    doc["updated_at"] = now
    await db.meetings.insert_one(doc)
    return _enrich(_clean(doc))


@meetings_router.put("/meetings/{meeting_id}")
async def update_meeting(meeting_id: str, body: MeetingIn, _: dict = Depends(require_admin)):
    existing = await db.meetings.find_one({"id": meeting_id})
    if not existing:
        raise HTTPException(status_code=404, detail="Meeting not found")
    doc = body.model_dump()
    doc.update(_derive_period(body.meeting_date))
    doc["updated_at"] = datetime.now(timezone.utc).isoformat()
    await db.meetings.update_one({"id": meeting_id}, {"$set": doc})
    updated = await db.meetings.find_one({"id": meeting_id}, {"_id": 0})
    return _enrich(updated)


@meetings_router.delete("/meetings/{meeting_id}")
async def delete_meeting(meeting_id: str, _: dict = Depends(require_admin)):
    res = await db.meetings.delete_one({"id": meeting_id})
    if res.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Meeting not found")
    return {"ok": True}


@meetings_router.get("/analytics/trends")
async def trends(_: dict = Depends(get_current_user)):
    docs = await db.meetings.find({}, {"_id": 0}).sort("meeting_date", 1).to_list(500)
    weekly = []
    monthly_map = {}
    for d in docs:
        e = _enrich(d)["summary"]
        weekly.append({
            "meeting_id": d["id"],
            "meeting_date": d["meeting_date"],
            "week_label": d.get("week_label", ""),
            "period_start": d.get("period_start", ""),
            "period_end": d.get("period_end", ""),
            **e,
        })
        key = f"{d.get('year')}-{d.get('month'):02d}" if d.get("month") else d["meeting_date"][:7]
        m = monthly_map.setdefault(key, {"month_key": key, "count": 0, "total_outstanding": 0,
                                         "d90": 0, "d60": 0, "d30": 0, "othera": 0,
                                         "total_new_target": 0, "avg_coll_pct_sum": 0})
        m["count"] += 1
        for k in ("total_outstanding", "d90", "d60", "d30", "othera", "total_new_target"):
            m[k] += e[k]
        m["avg_coll_pct_sum"] += e["avg_coll_pct"]
    monthly = []
    for key in sorted(monthly_map.keys()):
        m = monthly_map[key]
        cnt = max(m["count"], 1)
        monthly.append({
            "month_key": key,
            "total_outstanding": round(m["total_outstanding"] / cnt, 2),
            "d90": round(m["d90"] / cnt, 2),
            "d60": round(m["d60"] / cnt, 2),
            "d30": round(m["d30"] / cnt, 2),
            "othera": round(m["othera"] / cnt, 2),
            "total_new_target": round(m["total_new_target"] / cnt, 2),
            "avg_coll_pct": round(m["avg_coll_pct_sum"] / cnt, 2),
            "meetings": m["count"],
        })
    return {"weekly": weekly, "monthly": monthly}


@meetings_router.post("/extract")
async def extract_file(file: UploadFile = File(...), _: dict = Depends(require_admin)):
    filename = file.filename or "upload"
    suffix = os.path.splitext(filename)[1] or ".bin"
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
    try:
        content = await file.read()
        tmp.write(content)
        tmp.close()
        data = await extraction.extract_meeting(tmp.name, filename)
        return {"ok": True, "data": data}
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"Extraction failed: {exc}")
    finally:
        try:
            os.unlink(tmp.name)
        except Exception:
            pass
