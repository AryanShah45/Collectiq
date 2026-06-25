import uuid
from datetime import datetime, timezone, date
from typing import List

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, UploadFile, File
from pydantic import BaseModel, Field

from db import db
from auth import get_current_user, require_admin
import extraction
import os
import tempfile
import logging

logger = logging.getLogger(__name__)
meetings_router = APIRouter(prefix="/api", tags=["meetings"])


def _now_iso():
    return datetime.now(timezone.utc).isoformat()


# ---------- models ----------
class Amount(BaseModel):
    mbs: float = 0
    mcorp: float = 0


class Aging(BaseModel):
    d90: Amount = Field(default_factory=Amount)
    d60: Amount = Field(default_factory=Amount)
    d30: Amount = Field(default_factory=Amount)
    othera: Amount = Field(default_factory=Amount)


class RepEntry(BaseModel):
    name: str
    aging: Aging = Field(default_factory=Aging)
    weekly_collection: float = 0
    last_week_target: float = 0
    working_days: int = 6


class PurchaseSales(BaseModel):
    value: Amount = Field(default_factory=Amount)
    tons: Amount = Field(default_factory=Amount)


class Branch(BaseModel):
    name: str
    purchase: PurchaseSales = Field(default_factory=PurchaseSales)
    sales: PurchaseSales = Field(default_factory=PurchaseSales)


class Quotation(BaseModel):
    prepair: Amount = Field(default_factory=Amount)
    conform: Amount = Field(default_factory=Amount)
    pending: Amount = Field(default_factory=Amount)
    under_process: Amount = Field(default_factory=Amount)
    not_conform: Amount = Field(default_factory=Amount)


class MarketingRep(BaseModel):
    name: str
    visit: Amount = Field(default_factory=Amount)
    inquiry: Amount = Field(default_factory=Amount)
    inquiry_conform: Amount = Field(default_factory=Amount)
    order_loss: Amount = Field(default_factory=Amount)


class MeetingIn(BaseModel):
    title: str = "Weekly Collection Meeting"
    meeting_date: str
    period_start: str = ""
    period_end: str = ""
    notes: str = ""
    reps: List[RepEntry] = Field(default_factory=list)
    branches: List[Branch] = Field(default_factory=list)
    quotation: Quotation = Field(default_factory=Quotation)
    marketing_reps: List[MarketingRep] = Field(default_factory=list)


# ---------- helpers ----------
def _derive_period(meeting_date: str):
    try:
        d = date.fromisoformat(meeting_date[:10])
    except Exception:
        d = datetime.now(timezone.utc).date()
    iso = d.isocalendar()
    return {"week_label": f"{iso[0]}-W{iso[1]:02d}", "month": d.month, "year": d.year}


def _amt_sum(a):
    a = a or {}
    return (a.get("mbs", 0) or 0) + (a.get("mcorp", 0) or 0)


def _rep_total(rep: dict) -> float:
    ag = rep.get("aging", {})
    return sum(_amt_sum(ag.get(b)) for b in ("d90", "d60", "d30", "othera"))


def _enrich(meeting: dict) -> dict:
    d90 = d60 = d30 = other = collected = 0.0
    for rep in meeting.get("reps", []):
        ag = rep.get("aging", {})
        d90 += _amt_sum(ag.get("d90"))
        d60 += _amt_sum(ag.get("d60"))
        d30 += _amt_sum(ag.get("d30"))
        other += _amt_sum(ag.get("othera"))
        collected += rep.get("weekly_collection", 0) or 0
    total_outstanding = d90 + d60 + d30 + other

    p_val = s_val = p_tons = s_tons = 0.0
    for b in meeting.get("branches", []):
        p_val += _amt_sum(b.get("purchase", {}).get("value"))
        s_val += _amt_sum(b.get("sales", {}).get("value"))
        p_tons += _amt_sum(b.get("purchase", {}).get("tons"))
        s_tons += _amt_sum(b.get("sales", {}).get("tons"))

    q = meeting.get("quotation", {})
    meeting["summary"] = {
        "total_outstanding": round(total_outstanding, 2),
        "d90": round(d90, 2), "d60": round(d60, 2), "d30": round(d30, 2), "othera": round(other, 2),
        "collected": round(collected, 2),
        "coll_pct": round(collected / total_outstanding * 100, 2) if total_outstanding else 0,
        "new_target_total": round(total_outstanding, 2),
        "rep_count": len(meeting.get("reps", [])),
        "branch_count": len(meeting.get("branches", [])),
        "marketing_rep_count": len(meeting.get("marketing_reps", [])),
        "purchase_value": round(p_val, 2), "sales_value": round(s_val, 2),
        "purchase_tons": round(p_tons, 2), "sales_tons": round(s_tons, 2),
        "quotation_prepared": _amt_sum(q.get("prepair")),
        "quotation_confirmed": _amt_sum(q.get("conform")),
    }
    return meeting


def _clean(meeting: dict) -> dict:
    meeting.pop("_id", None)
    return meeting


async def _attach_last_week_targets(doc: dict, exclude_id: str = None):
    query = {"meeting_date": {"$lt": doc["meeting_date"]}}
    if exclude_id:
        query["id"] = {"$ne": exclude_id}
    prior = await db.meetings.find_one(query, sort=[("meeting_date", -1)], projection={"_id": 0})
    if not prior:
        return
    prior_map = {r["name"].strip().lower(): _rep_total(r) for r in prior.get("reps", [])}
    for r in doc.get("reps", []):
        key = r["name"].strip().lower()
        if key in prior_map:
            r["last_week_target"] = prior_map[key]


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
    now = _now_iso()
    doc = body.model_dump()
    doc.update(_derive_period(body.meeting_date))
    doc["id"] = str(uuid.uuid4())
    doc["created_by"] = admin.get("name") or admin.get("email")
    doc["created_at"] = now
    doc["updated_at"] = now
    await _attach_last_week_targets(doc)
    await db.meetings.insert_one(doc)
    return _enrich(_clean(doc))


@meetings_router.put("/meetings/{meeting_id}")
async def update_meeting(meeting_id: str, body: MeetingIn, _: dict = Depends(require_admin)):
    existing = await db.meetings.find_one({"id": meeting_id})
    if not existing:
        raise HTTPException(status_code=404, detail="Meeting not found")
    doc = body.model_dump()
    doc.update(_derive_period(body.meeting_date))
    doc["updated_at"] = _now_iso()
    await _attach_last_week_targets(doc, exclude_id=meeting_id)
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
    for d in docs:
        e = _enrich(d)["summary"]
        weekly.append({
            "meeting_id": d["id"], "meeting_date": d["meeting_date"],
            "week_label": d.get("week_label", ""), "period_end": d.get("period_end", ""),
            **e,
        })
    return {"weekly": weekly}


# ---------- async extraction ----------
async def _run_extraction(job_id: str, content: bytes, filename: str):
    suffix = os.path.splitext(filename)[1] or ".bin"
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
    try:
        tmp.write(content)
        tmp.close()
        data = await extraction.extract_meeting(tmp.name, filename)
        await db.extract_jobs.update_one(
            {"id": job_id}, {"$set": {"status": "done", "data": data, "updated_at": _now_iso()}})
    except Exception as exc:
        logger.error("Extraction job %s failed: %s", job_id, exc)
        await db.extract_jobs.update_one(
            {"id": job_id},
            {"$set": {"status": "error",
                      "error": "We couldn't read this file. Please check it's a valid meeting PDF/Excel and try again.",
                      "updated_at": _now_iso()}})
    finally:
        try:
            os.unlink(tmp.name)
        except Exception:
            pass


@meetings_router.post("/extract")
async def extract_file(background: BackgroundTasks, file: UploadFile = File(...),
                       admin: dict = Depends(require_admin)):
    content = await file.read()
    job_id = str(uuid.uuid4())
    await db.extract_jobs.insert_one({
        "id": job_id, "status": "processing", "filename": file.filename or "upload",
        "created_by": admin.get("email"), "created_at": _now_iso(),
    })
    background.add_task(_run_extraction, job_id, content, file.filename or "upload")
    return {"job_id": job_id, "status": "processing"}


@meetings_router.get("/extract/{job_id}")
async def extract_status(job_id: str, _: dict = Depends(require_admin)):
    job = await db.extract_jobs.find_one({"id": job_id}, {"_id": 0})
    if not job:
        raise HTTPException(status_code=404, detail="Extraction job not found")
    return job
