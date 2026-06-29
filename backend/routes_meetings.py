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
    d15: Amount = Field(default_factory=Amount)  # 15-day slab — MCORP only (mbs stays 0)
    othera: Amount = Field(default_factory=Amount)


class RepEntry(BaseModel):
    name: str
    aging: Aging = Field(default_factory=Aging)
    weekly_collection: Amount = Field(default_factory=Amount)
    last_week_target: float = 0
    working_days: int = 6


class PurchaseSales(BaseModel):
    # Branches are reported in tonnage; rupee value is optional per branch
    # (the weekly report only prints rupee totals at the company level).
    tons: Amount = Field(default_factory=Amount)
    value: Amount = Field(default_factory=Amount)


class Branch(BaseModel):
    name: str
    purchase: PurchaseSales = Field(default_factory=PurchaseSales)
    sales: PurchaseSales = Field(default_factory=PurchaseSales)


class BranchSale(BaseModel):
    """A marketing person's sales tonnage attributed to one branch (MBS/MCORP)."""
    name: str = ""
    tons: Amount = Field(default_factory=Amount)


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
    # Per-person sales bifurcated by branch (TONS), split MBS/MCORP.
    branch_sales: List[BranchSale] = Field(default_factory=list)
    # Per-person targets entered manually; achieve% is computed (not stored).
    target_tons: float = 0
    target_tons_achieve_pct: float = 0
    target_party: float = 0
    target_party_achieve_pct: float = 0


class Financials(BaseModel):
    # Company-wide rupee figures taken straight from the report's bottom summary.
    sales_value: Amount = Field(default_factory=Amount)
    purchase_value: Amount = Field(default_factory=Amount)


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
    financials: Financials = Field(default_factory=Financials)


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
    """Total outstanding for a rep: all buckets (incl. 15-day MCORP & OTHER)."""
    ag = rep.get("aging", {})
    return sum(_amt_sum(ag.get(b)) for b in ("d90", "d60", "d30", "d15", "othera"))


def _rep_new_target(rep: dict) -> float:
    """New Target for a rep = (MBS: 90+60+30) + (MCORP: 90+60+30+15).
    Excludes the OTHER bucket. The 15-day slab only exists for MCORP, so summing
    d15 across both companies is fine (its MBS side is always 0)."""
    ag = rep.get("aging", {})
    return sum(_amt_sum(ag.get(b)) for b in ("d90", "d60", "d30", "d15"))


def _enrich(meeting: dict) -> dict:
    d90 = d60 = d30 = d15 = other = collected = 0.0
    for rep in meeting.get("reps", []):
        ag = rep.get("aging", {})
        d90 += _amt_sum(ag.get("d90"))
        d60 += _amt_sum(ag.get("d60"))
        d30 += _amt_sum(ag.get("d30"))
        d15 += _amt_sum(ag.get("d15"))
        other += _amt_sum(ag.get("othera"))
        collected += _amt_sum(rep.get("weekly_collection")) if isinstance(rep.get("weekly_collection"), dict) else (rep.get("weekly_collection", 0) or 0)
    total_outstanding = d90 + d60 + d30 + d15 + other
    new_target = d90 + d60 + d30 + d15     # (MBS 90+60+30) + (MCORP 90+60+30+15); excludes OTHER

    p_tons = s_tons = 0.0
    p_val = s_val = 0.0
    for b in meeting.get("branches", []):
        p_tons += _amt_sum(b.get("purchase", {}).get("tons"))
        s_tons += _amt_sum(b.get("sales", {}).get("tons"))
        p_val += _amt_sum(b.get("purchase", {}).get("value"))
        s_val += _amt_sum(b.get("sales", {}).get("value"))

    # Rupee sales/purchase totals: the report prints these only at company level,
    # so prefer the meeting-level financials block; fall back to per-branch sums.
    fin = meeting.get("financials") or {}
    fin_sales = _amt_sum(fin.get("sales_value"))
    fin_purchase = _amt_sum(fin.get("purchase_value"))
    sales_value = fin_sales if fin_sales else s_val
    purchase_value = fin_purchase if fin_purchase else p_val

    q = meeting.get("quotation", {})
    meeting["summary"] = {
        "total_outstanding": round(total_outstanding, 2),
        "d90": round(d90, 2), "d60": round(d60, 2), "d30": round(d30, 2),
        "d15": round(d15, 2), "othera": round(other, 2),
        "collected": round(collected, 2),
        "coll_pct": round(collected / new_target * 100, 2) if new_target else 0,
        "new_target_total": round(new_target, 2),
        "rep_count": len(meeting.get("reps", [])),
        "branch_count": len(meeting.get("branches", [])),
        "marketing_rep_count": len(meeting.get("marketing_reps", [])),
        "purchase_tons": round(p_tons, 2), "sales_tons": round(s_tons, 2),
        "purchase_value": round(purchase_value, 2), "sales_value": round(sales_value, 2),
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
    prior_map = {r["name"].strip().lower(): _rep_new_target(r) for r in prior.get("reps", [])}
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
    # last_week_target is entered manually by the user (no auto-derivation).
    await db.meetings.insert_one(doc)
    from routes_notion import maybe_push
    await maybe_push(dict(doc))
    return _enrich(_clean(doc))


@meetings_router.put("/meetings/{meeting_id}")
async def update_meeting(meeting_id: str, body: MeetingIn, _: dict = Depends(require_admin)):
    existing = await db.meetings.find_one({"id": meeting_id})
    if not existing:
        raise HTTPException(status_code=404, detail="Meeting not found")
    doc = body.model_dump()
    doc.update(_derive_period(body.meeting_date))
    doc["updated_at"] = _now_iso()
    # last_week_target is entered manually by the user (no auto-derivation).
    await db.meetings.update_one({"id": meeting_id}, {"$set": doc})
    updated = await db.meetings.find_one({"id": meeting_id}, {"_id": 0})
    from routes_notion import maybe_push
    await maybe_push(dict(updated))
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


# ---------- export (PDF / Excel) ----------
async def _company_names():
    from routes_settings import get_settings_doc
    s = await get_settings_doc()
    return s.get("company_a", "MBS"), s.get("company_b", "MCORP")


@meetings_router.get("/analytics/report.pdf")
async def analytics_report(_: dict = Depends(get_current_user)):
    from fastapi.responses import Response
    import export_report
    docs = await db.meetings.find({}, {"_id": 0}).sort("meeting_date", 1).to_list(500)
    weeks = []
    for d in docs:
        s = _enrich(d)["summary"]
        visits = sum(_amt_sum(m.get("visit")) for m in d.get("marketing_reps", []))
        inquiries = sum(_amt_sum(m.get("inquiry")) for m in d.get("marketing_reps", []))
        confirmed = sum(_amt_sum(m.get("inquiry_conform")) for m in d.get("marketing_reps", []))
        order_loss = sum(_amt_sum(m.get("order_loss")) for m in d.get("marketing_reps", []))
        branches = [{
            "name": b.get("name", ""),
            "sales_tons": _amt_sum(b.get("sales", {}).get("tons")),
            "purchase_tons": _amt_sum(b.get("purchase", {}).get("tons")),
        } for b in d.get("branches", [])]
        weeks.append({
            "date": d.get("meeting_date", ""),
            "outstanding": s["total_outstanding"], "d90": s["d90"], "d60": s["d60"],
            "d30": s["d30"], "othera": s["othera"], "collected": s["collected"], "coll_pct": s["coll_pct"],
            "sales_value": s["sales_value"], "purchase_value": s["purchase_value"],
            "sales_tons": s["sales_tons"], "purchase_tons": s["purchase_tons"],
            "visits": visits, "inquiries": inquiries, "confirmed": confirmed, "order_loss": order_loss,
            "conv": round(confirmed / inquiries * 100, 1) if inquiries else 0,
            "branches": branches,
        })
    ca, cb = await _company_names()
    data = export_report.build_trends_pdf(weeks, ca, cb)
    headers = {"Content-Disposition": 'attachment; filename="collectiq-trends-report.pdf"'}
    return Response(content=data, media_type="application/pdf", headers=headers)


@meetings_router.get("/reps/{name}/history")
async def rep_history(name: str, _: dict = Depends(get_current_user)):
    target = (name or "").strip().lower()
    docs = await db.meetings.find({}, {"_id": 0}).sort("meeting_date", 1).to_list(500)
    series = []
    for d in docs:
        rep = next((r for r in d.get("reps", []) if (r.get("name") or "").strip().lower() == target), None)
        if not rep:
            continue
        ag = rep.get("aging", {})
        wc = rep.get("weekly_collection")
        coll = _amt_sum(wc) if isinstance(wc, dict) else (wc or 0)
        out = _rep_total(rep)
        nt = sum(_amt_sum(ag.get(b)) for b in ("d90", "d60", "d30", "d15"))
        series.append({
            "meeting_date": d.get("meeting_date"), "week_label": d.get("week_label", ""),
            "d90": round(_amt_sum(ag.get("d90")), 2), "d60": round(_amt_sum(ag.get("d60")), 2),
            "d30": round(_amt_sum(ag.get("d30")), 2),
            "d15": round(_amt_sum(ag.get("d15")), 2), "othera": round(_amt_sum(ag.get("othera")), 2),
            "outstanding": round(out, 2), "collected": round(coll, 2),
            "coll_pct": round(coll / nt * 100, 2) if nt else 0,
        })
    return {"name": name, "points": series}


@meetings_router.get("/meetings/{meeting_id}/briefing")
async def meeting_briefing(meeting_id: str, _: dict = Depends(get_current_user)):
    import briefing
    doc = await db.meetings.find_one({"id": meeting_id}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Meeting not found")
    prev = await db.meetings.find_one(
        {"meeting_date": {"$lt": doc.get("meeting_date", "")}}, {"_id": 0},
        sort=[("meeting_date", -1)],
    )
    return await briefing.build_briefing(doc, prev)


@meetings_router.get("/meetings/{meeting_id}/export.{fmt}")
async def export_meeting(meeting_id: str, fmt: str, _: dict = Depends(get_current_user)):
    from fastapi.responses import Response
    import export_report
    doc = await db.meetings.find_one({"id": meeting_id}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Meeting not found")
    meeting = _enrich(doc)
    ca, cb = await _company_names()
    date = meeting.get("meeting_date", "report")
    if fmt == "pdf":
        data = export_report.build_pdf(meeting, ca, cb)
        media = "application/pdf"
    elif fmt in ("xlsx", "excel"):
        data = export_report.build_xlsx(meeting, ca, cb)
        media = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        fmt = "xlsx"
    else:
        raise HTTPException(status_code=400, detail="Format must be pdf or xlsx")
    headers = {"Content-Disposition": f'attachment; filename="collectiq-{date}.{fmt}"'}
    return Response(content=data, media_type=media, headers=headers)


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
        "created_dt": datetime.now(timezone.utc),
    })
    background.add_task(_run_extraction, job_id, content, file.filename or "upload")
    return {"job_id": job_id, "status": "processing"}


@meetings_router.get("/extract/{job_id}")
async def extract_status(job_id: str, _: dict = Depends(require_admin)):
    job = await db.extract_jobs.find_one({"id": job_id}, {"_id": 0})
    if not job:
        raise HTTPException(status_code=404, detail="Extraction job not found")
    return job
