import uuid
from datetime import datetime, timezone, date

from db import db


def amt(mbs, mcorp):
    return {"mbs": float(mbs), "mcorp": float(mcorp)}


# Real numbers from "MEETING DT - 24-06-2025.pdf" (period 14-06-25 to 20-06-25)
# coll_per_day -> weekly_collection = coll_per_day * 6
REAL_REPS = [
    {"name": "Arun",
     "aging": {"d90": amt(2734927, 149663), "d60": amt(5947632, 498313),
               "d30": amt(15224253, 2577513), "othera": amt(16029753, 14197367)},
     "weekly_collection": round(881420.33 * 6, 2)},
    {"name": "Ghanshyam",
     "aging": {"d90": amt(5489021, 839554), "d60": amt(5609527, 34102),
               "d30": amt(16215495, 72525), "othera": amt(17096670, 424485)},
     "weekly_collection": round(844068.50 * 6, 2)},
    {"name": "Kamlesh",
     "aging": {"d90": amt(4725029, 661073), "d60": amt(3213859, 2588841),
               "d30": amt(5372816, 7645985), "othera": amt(12829686, 4646513)},
     "weekly_collection": round(540005.50 * 6, 2)},
    {"name": "Ankleshwar",
     "aging": {"d90": amt(7662440, 1265645), "d60": amt(4126191, 19569),
               "d30": amt(10823707, 0), "othera": amt(7750632, 974)},
     "weekly_collection": round(438908.17 * 6, 2)},
    {"name": "Umeshbhai",
     "aging": {"d90": amt(1403862, 275279), "d60": amt(1000478, 209051),
               "d30": amt(4661779, 1119480), "othera": amt(15486543, 2787991)},
     "weekly_collection": round(412421.50 * 6, 2)},
]

# Branch tonnage (from the PDF); value derived as tons * RATE for the sample
BRANCH_TONS = [
    {"name": "Sachin",     "p": (79.15, 46.83), "s": (59.76, 60.90)},
    {"name": "Ankleshwar", "p": (14.75, 0.00),  "s": (55.03, 0.00)},
    {"name": "Udhna",      "p": (12.97, 2.99),  "s": (29.03, 0.78)},
    {"name": "Kadodra",    "p": (35.68, 14.87), "s": (24.93, 2.78)},
    {"name": "Direct Sale", "p": (20.00, 5.00), "s": (30.00, 8.00)},
]

QUOTATION = {
    "prepair": amt(95, 38), "conform": amt(59, 20), "pending": amt(32, 14),
    "under_process": amt(32, 14), "not_conform": amt(4, 4),
}

# Marketing people exactly as in the report: Hitesh, Ghanshyam, Meetbhai.
# visit/inquiry/inquiry_conform/order_loss are (MBS, MCORP) counts.
MARKETING_REPS = [
    {"name": "Hitesh", "visit": amt(0, 0), "inquiry": amt(0, 0),
     "inquiry_conform": amt(0, 0), "order_loss": amt(0, 0),
     "branch_sales": [{"name": "Sachin", "tons": amt(10, 5)},
                      {"name": "Udhna", "tons": amt(8, 0)}],
     "target_tons": 50, "target_party": 10},
    {"name": "Ghanshyam", "visit": amt(0, 5), "inquiry": amt(0, 0),
     "inquiry_conform": amt(0, 3), "order_loss": amt(0, 0),
     "branch_sales": [{"name": "Ankleshwar", "tons": amt(20, 10)},
                      {"name": "Kadodra", "tons": amt(15, 5)}],
     "target_tons": 50, "target_party": 10},
    {"name": "Meetbhai", "visit": amt(35, 0), "inquiry": amt(4, 0),
     "inquiry_conform": amt(0, 0), "order_loss": amt(0, 0),
     "branch_sales": [{"name": "Sachin", "tons": amt(5, 2)}],
     "target_tons": 40, "target_party": 40},
]

# Company-wide rupee figures from the report's bottom summary (split MBS/MCORP).
REAL_FINANCIALS = {
    "sales_value": amt(14659825, 5695227),      # TOTAL SALES   = 20,355,052
    "purchase_value": amt(3278895, 4046736),    # TOTAL PURCHASE =  7,325,631
}

# (meeting_date, period_start, period_end, scale, coll_scale)
WEEKS = [
    ("2025-05-30", "2025-05-24", "2025-05-30", 1.15, 0.88),
    ("2025-06-06", "2025-05-31", "2025-06-06", 1.10, 0.92),
    ("2025-06-13", "2025-06-07", "2025-06-13", 1.05, 0.96),
    ("2025-06-24", "2025-06-14", "2025-06-20", 1.00, 1.00),
]


def _build_branches(scale):
    out = []
    for b in BRANCH_TONS:
        pt_m, pt_c = b["p"][0] * scale, b["p"][1] * scale
        st_m, st_c = b["s"][0] * scale, b["s"][1] * scale
        out.append({
            "name": b["name"],
            # Tonnage is from the report; rupee value per branch is left at 0
            # (the report only gives rupee totals at the company level).
            "purchase": {"tons": amt(round(pt_m, 2), round(pt_c, 2)), "value": amt(0, 0)},
            "sales": {"tons": amt(round(st_m, 2), round(st_c, 2)), "value": amt(0, 0)},
        })
    return out


def _build_financials(scale):
    f = REAL_FINANCIALS
    return {
        "sales_value": amt(round(f["sales_value"]["mbs"] * scale),
                           round(f["sales_value"]["mcorp"] * scale)),
        "purchase_value": amt(round(f["purchase_value"]["mbs"] * scale),
                              round(f["purchase_value"]["mcorp"] * scale)),
    }


def _build_reps(scale, coll_scale):
    out = []
    for r in REAL_REPS:
        ag = {}
        for b, v in r["aging"].items():
            ag[b] = amt(round(v["mbs"] * scale), round(v["mcorp"] * scale))
        # 15-day slab — MCORP only (sample value derived from the 30-day MCORP dues).
        ag["d15"] = amt(0, round(ag["d30"]["mcorp"] * 0.3, 2))
        out.append({
            "name": r["name"], "aging": ag,
            "weekly_collection": round(r["weekly_collection"] * coll_scale, 2),
            "last_week_target": 0, "working_days": 6,
        })
    return out


def _rep_total(rep):
    # New Target = (MBS 90+60+30) + (MCORP 90+60+30+15); excludes OTHER. Chains last_week_target.
    return sum((rep["aging"][b]["mbs"] + rep["aging"][b]["mcorp"]) for b in ("d90", "d60", "d30", "d15"))


def _derive(meeting_date):
    d = date.fromisoformat(meeting_date)
    iso = d.isocalendar()
    return {"week_label": f"{iso[0]}-W{iso[1]:02d}", "month": d.month, "year": d.year}


async def seed_meetings():
    if await db.meetings.count_documents({}) > 0:
        return
    now = _now_iso = datetime.now(timezone.utc).isoformat()
    prev_totals = {}
    for mdate, pstart, pend, scale, coll_scale in WEEKS:
        is_real = scale == 1.00
        reps = REAL_REPS_FULL() if is_real else _build_reps(scale, coll_scale)
        # chain last week target = previous week's rep total outstanding
        for r in reps:
            key = r["name"].strip().lower()
            if key in prev_totals:
                r["last_week_target"] = prev_totals[key]
        doc = {
            "id": str(uuid.uuid4()),
            "title": "Weekly Collection Meeting",
            "meeting_date": mdate, "period_start": pstart, "period_end": pend,
            "notes": "" if is_real else "Historical week (auto-generated baseline for trends).",
            "reps": reps,
            "branches": _build_branches(scale),
            "quotation": QUOTATION,
            "marketing_reps": MARKETING_REPS,
            "financials": _build_financials(scale),
            "created_by": "System Seed",
            "created_at": now, "updated_at": now,
        }
        doc.update(_derive(mdate))
        await db.meetings.insert_one(doc)
        prev_totals = {r["name"].strip().lower(): _rep_total(r) for r in reps}


def REAL_REPS_FULL():
    out = []
    for r in REAL_REPS:
        ag = {b: amt(v["mbs"], v["mcorp"]) for b, v in r["aging"].items()}
        # 15-day slab — MCORP only (sample value derived from the 30-day MCORP dues).
        ag["d15"] = amt(0, round(ag["d30"]["mcorp"] * 0.3, 2))
        out.append({"name": r["name"], "aging": ag,
                    "weekly_collection": r["weekly_collection"],
                    "last_week_target": 0, "working_days": 6})
    return out
