"""Weekly meeting briefing.

Two layers:
  1. Deterministic risk flags computed from the data (always available, no key).
  2. An optional AI-written narrative via Gemini (if GEMINI_API_KEY is set);
     otherwise a clean rule-based summary is returned.
"""
import os

from routes_meetings import _amt_sum, _rep_total, _enrich


def _coll(rep):
    wc = rep.get("weekly_collection")
    return _amt_sum(wc) if isinstance(wc, dict) else (wc or 0)


def _inr(n):
    n = float(n or 0)
    if abs(n) >= 1e7:
        return f"Rs {n/1e7:.2f} Cr"
    if abs(n) >= 1e5:
        return f"Rs {n/1e5:.2f} L"
    return f"Rs {n:,.0f}"


def _by_name(reps):
    return {(r.get("name") or "").strip().lower(): r for r in reps}


def compute_flags(meeting: dict, prev: dict | None) -> list:
    flags = []
    reps = meeting.get("reps", [])
    prev_reps = _by_name(prev.get("reps", [])) if prev else {}

    # Per-rep checks
    for rep in reps:
        name = rep.get("name", "Unknown")
        ag = rep.get("aging", {})
        d90 = _amt_sum(ag.get("d90"))
        out = _rep_total(rep)
        nt = sum(_amt_sum(ag.get(b)) for b in ("d90", "d60", "d30"))
        coll = _coll(rep)
        pct = (coll / nt * 100) if nt else 0

        prev_rep = prev_reps.get(name.strip().lower())
        if prev_rep:
            prev_d90 = _amt_sum(prev_rep.get("aging", {}).get("d90"))
            if d90 > prev_d90 * 1.05 and d90 - prev_d90 > 10000:
                flags.append({"severity": "high", "title": f"{name}: 90-day overdue rising",
                              "detail": f"90-day book grew from {_inr(prev_d90)} to {_inr(d90)}."})
            prev_out = _rep_total(prev_rep)
            if out > prev_out * 1.1 and out - prev_out > 50000:
                flags.append({"severity": "medium", "title": f"{name}: outstanding climbing",
                              "detail": f"Total outstanding up from {_inr(prev_out)} to {_inr(out)}."})

        if nt and pct < 6:
            flags.append({"severity": "high", "title": f"{name}: low collection rate",
                          "detail": f"Collected only {pct:.1f}% of the {_inr(nt)} target this week."})
        elif nt and pct < 12:
            flags.append({"severity": "medium", "title": f"{name}: below target",
                          "detail": f"Collection at {pct:.1f}% (collected {_inr(coll)})."})

    # Branch checks
    for b in meeting.get("branches", []):
        s_tons = _amt_sum(b.get("sales", {}).get("tons"))
        if s_tons == 0:
            flags.append({"severity": "medium", "title": f"{b.get('name','Branch')}: no sales",
                          "detail": "Zero sales tonnage recorded this week."})

    # Marketing checks
    for m in meeting.get("marketing_reps", []):
        loss = _amt_sum(m.get("order_loss"))
        if loss > 0:
            flags.append({"severity": "medium", "title": f"{m.get('name','')}: orders lost",
                          "detail": f"{loss:.0f} order(s) lost this week."})
        ach = m.get("target_tons_achieve_pct", 0)
        if m.get("target_tons", 0) and ach < 50:
            flags.append({"severity": "low", "title": f"{m.get('name','')}: marketing target low",
                          "detail": f"Tonnage target achievement at {ach:.0f}%."})

    order = {"high": 0, "medium": 1, "low": 2}
    flags.sort(key=lambda f: order.get(f["severity"], 3))
    return flags


def _deterministic_narrative(meeting, prev, flags) -> str:
    s = meeting.get("summary", {})
    parts = []
    out = s.get("total_outstanding", 0)
    coll = s.get("collected", 0)
    pct = s.get("coll_pct", 0)
    line = f"Total outstanding stands at {_inr(out)}, with {_inr(coll)} collected this week ({pct:.1f}% of target)."
    if prev:
        pout = prev.get("summary", {}).get("total_outstanding", 0)
        if pout:
            delta = (out - pout) / pout * 100
            dirn = "up" if delta > 0 else "down"
            line += f" Outstanding is {dirn} {abs(delta):.1f}% versus last week."
    parts.append(line)

    reps = meeting.get("reps", [])
    if reps:
        top = max(reps, key=_coll)
        parts.append(f"{top.get('name','')} led collections with {_inr(_coll(top))}.")
    highs = [f for f in flags if f["severity"] == "high"]
    if highs:
        parts.append("Priority issues: " + "; ".join(f["title"] for f in highs[:3]) + ".")
    elif flags:
        parts.append(f"{len(flags)} item(s) to watch this week.")
    else:
        parts.append("No major risks flagged this week.")
    return " ".join(parts)


async def build_narrative(meeting, prev, flags) -> tuple[str, bool]:
    """Returns (narrative, used_ai)."""
    key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not key:
        return _deterministic_narrative(meeting, prev, flags), False
    try:
        import asyncio
        from google import genai
        from google.genai import types

        s = meeting.get("summary", {})
        facts = {
            "outstanding": s.get("total_outstanding"), "collected": s.get("collected"),
            "coll_pct": s.get("coll_pct"), "d90": s.get("d90"),
            "sales_value": s.get("sales_value"), "purchase_value": s.get("purchase_value"),
            "prev_outstanding": (prev or {}).get("summary", {}).get("total_outstanding"),
            "flags": [f["title"] for f in flags[:8]],
            "reps": [{"name": r.get("name"), "collected": _coll(r), "outstanding": _rep_total(r)} for r in meeting.get("reps", [])],
        }
        prompt = (
            "You are a finance analyst preparing a brief for a weekly collections meeting. "
            "Write 3-4 crisp sentences (plain text, no markdown, Indian Rupee context) summarising the week: "
            "overall outstanding and collection performance, the week-over-week direction, who led, "
            "and the most important risks to discuss. Be specific and concise.\n\n"
            f"Data: {facts}"
        )
        client = genai.Client(api_key=key)
        model = os.environ.get("GEMINI_MODEL", "gemini-2.5-pro")

        def _run():
            resp = client.models.generate_content(model=model, contents=[prompt])
            return (resp.text or "").strip()

        text = await asyncio.to_thread(_run)
        if text:
            return text, True
    except Exception:
        pass
    return _deterministic_narrative(meeting, prev, flags), False


async def build_briefing(meeting_doc: dict, prev_doc: dict | None) -> dict:
    meeting = _enrich(meeting_doc)
    prev = _enrich(prev_doc) if prev_doc else None
    flags = compute_flags(meeting, prev)
    narrative, used_ai = await build_narrative(meeting, prev, flags)
    counts = {"high": 0, "medium": 0, "low": 0}
    for f in flags:
        counts[f["severity"]] = counts.get(f["severity"], 0) + 1
    return {"narrative": narrative, "ai": used_ai, "flags": flags, "counts": counts}
