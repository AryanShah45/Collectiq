"""Push meeting reports into a Notion database.

Robust by design: it looks up the database's own title property, always sets
that, auto-fills any Number columns whose names match our metrics (if you've
created them), and writes the full breakdown into the page body as text — so it
works with essentially any database layout, needing only that the integration
has access to it.

Configuration (either works; env wins):
  - env:  NOTION_TOKEN, NOTION_DATABASE_ID
  - or the admin saves them via POST /api/notion/config
"""
import os
import logging

import httpx
from fastapi import APIRouter, Body, Depends, HTTPException

from db import db
from auth import require_admin
from routes_meetings import _enrich

logger = logging.getLogger(__name__)
notion_router = APIRouter(prefix="/api/notion", tags=["notion"])

NOTION_API = "https://api.notion.com/v1"
NOTION_VERSION = "2022-06-28"
CONFIG_ID = "notion"


def _inr(n):
    n = float(n or 0)
    if abs(n) >= 1e7:
        return f"Rs {n/1e7:.2f} Cr"
    if abs(n) >= 1e5:
        return f"Rs {n/1e5:.2f} L"
    return f"Rs {n:,.0f}"


def _amt(a):
    a = a or {}
    return (a.get("mbs", 0) or 0), (a.get("mcorp", 0) or 0)


async def get_notion_config():
    token = os.environ.get("NOTION_TOKEN")
    database_id = os.environ.get("NOTION_DATABASE_ID")
    if not token or not database_id:
        doc = await db.settings.find_one({"id": CONFIG_ID}) or {}
        token = token or doc.get("token")
        database_id = database_id or doc.get("database_id")
    return token, database_id


def _headers(token):
    return {
        "Authorization": f"Bearer {token}",
        "Notion-Version": NOTION_VERSION,
        "Content-Type": "application/json",
    }


# metric name (lowercased) -> value getter from summary
def _metric_map(summary):
    return {
        "outstanding": summary.get("total_outstanding"),
        "total outstanding": summary.get("total_outstanding"),
        "collected": summary.get("collected"),
        "collection": summary.get("collected"),
        "coll %": summary.get("coll_pct"),
        "collection %": summary.get("coll_pct"),
        "sales": summary.get("sales_value"),
        "purchase": summary.get("purchase_value"),
        "90 days": summary.get("d90"),
        "90 day": summary.get("d90"),
    }


def _para(text):
    return {"object": "block", "type": "paragraph",
            "paragraph": {"rich_text": [{"type": "text", "text": {"content": text[:1900]}}]}}


def _h2(text):
    return {"object": "block", "type": "heading_2",
            "heading_2": {"rich_text": [{"type": "text", "text": {"content": text[:1900]}}]}}


def _build_blocks(meeting, ca, cb):
    s = meeting.get("summary", {})
    blocks = [
        _h2("Summary"),
        _para(f"Total Outstanding: {_inr(s.get('total_outstanding'))}  |  Collected: {_inr(s.get('collected'))}  "
              f"({s.get('coll_pct', 0):.1f}%)"),
        _para(f"90d: {_inr(s.get('d90'))}  |  60d: {_inr(s.get('d60'))}  |  30d: {_inr(s.get('d30'))}  |  "
              f"Other: {_inr(s.get('othera'))}"),
        _para(f"Sales: {_inr(s.get('sales_value'))}  |  Purchase: {_inr(s.get('purchase_value'))}  |  "
              f"Sales {s.get('sales_tons', 0):.1f} T  |  Purchase {s.get('purchase_tons', 0):.1f} T"),
        _h2("Collection by representative"),
    ]
    for rep in meeting.get("reps", []):
        ag = rep.get("aging", {})
        out = sum(sum(_amt(ag.get(b))) for b in ("d90", "d60", "d30", "othera"))
        coll = sum(_amt(rep.get("weekly_collection")))
        pct = (coll / out * 100) if out else 0
        blocks.append(_para(f"{rep.get('name','')}: Outstanding {_inr(out)}, Collected {_inr(coll)} ({pct:.1f}%)"))
    if meeting.get("branches"):
        blocks.append(_h2("Branches (Sales / Purchase tons)"))
        for b in meeting["branches"]:
            pm, pc = _amt(b.get("purchase", {}).get("tons"))
            sm, sc = _amt(b.get("sales", {}).get("tons"))
            blocks.append(_para(f"{b.get('name','')}: Purchase {pm+pc:.2f} T, Sales {sm+sc:.2f} T"))
    if meeting.get("marketing_reps"):
        blocks.append(_h2("Marketing"))
        for m in meeting["marketing_reps"]:
            v = sum(_amt(m.get("visit")))
            iq = sum(_amt(m.get("inquiry")))
            cf = sum(_amt(m.get("inquiry_conform")))
            blocks.append(_para(f"{m.get('name','')}: {v:.0f} visits, {iq:.0f} inquiries, {cf:.0f} confirmed, "
                                f"target {m.get('target_tons',0):.0f} T ({m.get('target_tons_achieve_pct',0):.0f}%)"))
    return blocks[:90]  # Notion caps children per request


async def push_meeting(meeting: dict) -> dict:
    """Create a Notion page for the meeting. Returns {ok, url|error}."""
    token, database_id = await get_notion_config()
    if not token or not database_id:
        return {"ok": False, "error": "Notion is not configured."}

    meeting = _enrich(meeting)
    s = meeting.get("summary", {})
    title_text = f"{meeting.get('title','Weekly Meeting')} — {meeting.get('meeting_date','')}"

    async with httpx.AsyncClient(timeout=30) as client:
        # 1) discover the database schema (title property + number columns)
        db_resp = await client.get(f"{NOTION_API}/databases/{database_id}", headers=_headers(token))
        if db_resp.status_code != 200:
            return {"ok": False, "error": f"Cannot access database ({db_resp.status_code}). "
                                          f"Share it with your integration."}
        props_schema = db_resp.json().get("properties", {})
        title_prop = next((name for name, p in props_schema.items() if p.get("type") == "title"), "Name")

        properties = {title_prop: {"title": [{"text": {"content": title_text}}]}}
        metrics = _metric_map(s)
        for name, p in props_schema.items():
            if p.get("type") == "number":
                val = metrics.get(name.strip().lower())
                if val is not None:
                    properties[name] = {"number": round(float(val), 2)}
            elif p.get("type") == "date" and name.strip().lower() in ("date", "meeting date"):
                if meeting.get("meeting_date"):
                    properties[name] = {"date": {"start": meeting["meeting_date"]}}

        payload = {
            "parent": {"database_id": database_id},
            "properties": properties,
            "children": _build_blocks(meeting, s.get("company_a", "MBS"), s.get("company_b", "MCORP")),
        }
        resp = await client.post(f"{NOTION_API}/pages", headers=_headers(token), json=payload)
        if resp.status_code in (200, 201):
            return {"ok": True, "url": resp.json().get("url")}
        return {"ok": False, "error": f"Notion rejected the page ({resp.status_code}): {resp.text[:300]}"}


async def maybe_push(meeting: dict):
    """Best-effort auto-push used after create/update; never raises."""
    try:
        token, database_id = await get_notion_config()
        if token and database_id:
            res = await push_meeting(meeting)
            if not res.get("ok"):
                logger.warning("Notion auto-sync failed: %s", res.get("error"))
    except Exception as exc:
        logger.warning("Notion auto-sync error: %s", exc)


# ---------- routes ----------
@notion_router.get("/status")
async def notion_status(_: dict = Depends(require_admin)):
    token, database_id = await get_notion_config()
    return {"connected": bool(token and database_id), "database_id": database_id or "",
            "via_env": bool(os.environ.get("NOTION_TOKEN"))}


@notion_router.post("/config")
async def notion_config(body: dict = Body(...), _: dict = Depends(require_admin)):
    token = (body.get("token") or "").strip()
    database_id = (body.get("database_id") or "").strip()
    update = {"id": CONFIG_ID, "database_id": database_id}
    if token:  # only overwrite token if a new one was supplied
        update["token"] = token
    await db.settings.update_one({"id": CONFIG_ID}, {"$set": update}, upsert=True)
    return {"ok": True, "connected": bool((token or (await get_notion_config())[0]) and database_id)}


@notion_router.post("/meetings/{meeting_id}")
async def push_one(meeting_id: str, _: dict = Depends(require_admin)):
    doc = await db.meetings.find_one({"id": meeting_id}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Meeting not found")
    res = await push_meeting(doc)
    if not res.get("ok"):
        raise HTTPException(status_code=400, detail=res.get("error", "Notion sync failed"))
    return res
