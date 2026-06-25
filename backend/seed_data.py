import uuid
from datetime import datetime, timezone, date

from db import db


def _amt(mbs, mcorp):
    return {"mbs": float(mbs), "mcorp": float(mcorp)}


# Real numbers extracted from "MEETING DT - 24-06-2025.pdf" (period 14-06-25 to 20-06-25)
REAL_REPS = [
    {"name": "Arun",
     "aging": {"d90": _amt(2734927, 149663), "d60": _amt(5947632, 498313),
               "d30": _amt(15224253, 2577513), "othera": _amt(0, 0)},
     "performance": {"purchase": _amt(0, 0), "sales": _amt(0, 0),
                     "coll_per_day": 881420.33, "coll_pct": 19.59,
                     "new_target": 27132301, "last_week_target": 19123762}},
    {"name": "Ghanshyam",
     "aging": {"d90": _amt(5489021, 839554), "d60": _amt(5609527, 34102),
               "d30": _amt(16215495, 72525), "othera": _amt(0, 0)},
     "performance": {"purchase": _amt(0, 0), "sales": _amt(0, 0),
                     "coll_per_day": 844068.50, "coll_pct": 18.62,
                     "new_target": 28260224, "last_week_target": 23225964}},
    {"name": "Kamlesh",
     "aging": {"d90": _amt(4725029, 661073), "d60": _amt(3213859, 2588841),
               "d30": _amt(5372816, 7645985), "othera": _amt(0, 0)},
     "performance": {"purchase": _amt(0, 0), "sales": _amt(0, 0),
                     "coll_per_day": 540005.50, "coll_pct": 14.15,
                     "new_target": 24207603, "last_week_target": 20900000}},
    {"name": "Ankleshwar",
     "aging": {"d90": _amt(7662440, 1265645), "d60": _amt(4126191, 19569),
               "d30": _amt(10823707, 0), "othera": _amt(0, 0)},
     "performance": {"purchase": _amt(0, 0), "sales": _amt(0, 0),
                     "coll_per_day": 438908.17, "coll_pct": 11.06,
                     "new_target": 23897552, "last_week_target": 24693486}},
    {"name": "Umeshbhai",
     "aging": {"d90": _amt(1403862, 275279), "d60": _amt(1000478, 209051),
               "d30": _amt(4661779, 1119480), "othera": _amt(0, 0)},
     "performance": {"purchase": _amt(0, 0), "sales": _amt(0, 0),
                     "coll_per_day": 412421.50, "coll_pct": 34.85,
                     "new_target": 8669929, "last_week_target": 4618939}},
]

REAL_QUOTATION = {
    "prepair": _amt(95, 38), "conform": _amt(59, 20), "pending": _amt(32, 14),
    "under_process": _amt(32, 14), "not_conform": _amt(4, 4),
}

# (meeting_date, period_start, period_end, outstanding_scale, coll_pct_delta)
WEEKS = [
    ("2025-05-30", "2025-05-24", "2025-05-30", 1.15, -6.0),
    ("2025-06-06", "2025-05-31", "2025-06-06", 1.10, -4.0),
    ("2025-06-13", "2025-06-07", "2025-06-13", 1.05, -2.0),
    ("2025-06-24", "2025-06-14", "2025-06-20", 1.00, 0.0),
]


def _scale_reps(scale, pct_delta):
    out = []
    for r in REAL_REPS:
        ag = {}
        for b, v in r["aging"].items():
            ag[b] = {"mbs": round(v["mbs"] * scale, 0), "mcorp": round(v["mcorp"] * scale, 0)}
        perf = dict(r["performance"])
        perf["coll_pct"] = round(max(perf["coll_pct"] + pct_delta, 0), 2)
        perf["coll_per_day"] = round(perf["coll_per_day"] * (0.92 + (scale - 1) * 0.3), 2)
        out.append({"name": r["name"], "aging": ag, "performance": perf})
    return out


def _derive(meeting_date):
    d = date.fromisoformat(meeting_date)
    iso = d.isocalendar()
    return {"week_label": f"{iso[0]}-W{iso[1]:02d}", "month": d.month, "year": d.year}


async def seed_meetings():
    if await db.meetings.count_documents({}) > 0:
        return
    now = datetime.now(timezone.utc).isoformat()
    for mdate, pstart, pend, scale, pct_delta in WEEKS:
        is_real = scale == 1.00
        reps = REAL_REPS if is_real else _scale_reps(scale, pct_delta)
        doc = {
            "id": str(uuid.uuid4()),
            "title": "Weekly Collection Meeting",
            "meeting_date": mdate,
            "period_start": pstart,
            "period_end": pend,
            "notes": "" if is_real else "Historical week (auto-generated baseline for trend analysis).",
            "reps": reps,
            "quotation": REAL_QUOTATION,
            "created_by": "System Seed",
            "created_at": now,
            "updated_at": now,
        }
        doc.update(_derive(mdate))
        await db.meetings.insert_one(doc)
