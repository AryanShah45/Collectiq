# CollectIQ — Changes (Phase 1 & 2)

Based on your real report **MEETING DT 24-06-2025** (period 14–20 Jun 2025).

## Phase 1 — Correct data model & real numbers ✅

**New Target fixed (was a real bug).**
The app previously calculated New Target as 90 + 60 + 30 + **OTHER**. Your report
defines it as **90 + 60 + 30 only** (OTHER excluded). Corrected everywhere it is
computed (dashboard KPIs, per-rep rows, backend summary, and the week-over-week
"last week target" chaining).

Verified against your PDF:
| Figure | Value | Matches report |
|---|---|---|
| Total Outstanding | ₹20,34,18,223 | ✓ |
| **New Target (corrected)** | **₹11,21,67,609** | ✓ (90+60+30) |
| Total Collection | ₹1,87,00,944 | ✓ |
| Collection % | 16.67% (collected ÷ new target) | — |

(New Target + Other now equals Total Outstanding exactly, as it should.)

**Branches are now tons-only.**
Removed the rupee (₹) value from branches across the whole app — data model,
seed data, AI extraction schema, the dashboard chart/table (the ₹/Tons toggle is
gone), and the data-entry form. Branches now show tonnage only, matching your
report. Verified totals: 207.24 T purchase / 233.21 T sales for the week.

## Phase 2 — AI extraction tuned to your report ✅

Rewrote the extraction so it uses Google's standard Gemini (free key) and taught
it the exact layout of *your* report: the two-column per-person blocks, the
"OTHERA" bucket, weekly-collection vs Coll/Day, tonnage-only branches, the
PREPAIR/CONFORM/PENDING quotation spellings, the marketing TOTAL VISIT/INQUIRY
lines, and the fact that a person and a branch can share a name (e.g. Ankleshwar)
and must stay separate.

To use it: add a free `GEMINI_API_KEY` to `backend/.env` (see DEPLOYMENT.md), then
upload your PDF on the Data Entry page.

## IMPORTANT — to see the corrected numbers

Your database still holds the *old* seeded data from your first run. The New
Target fix shows up immediately (it's recalculated on screen), but to refresh the
seeded sample weeks cleanly, reset the database once:

```
docker compose down -v
docker compose up -d --build
```

`down -v` wipes the local database so it re-seeds with the corrected figures.
Then log in again at http://localhost:8080.

## Phase 3 — Dashboard (next)

Not started yet — I'd like you to see the corrected app first, then tell me what
to sharpen. Some options I'd suggest: a dedicated "New Target" KPI card, a
collection %-vs-target gauge per rep, a 90-day-overdue ranking, and tidying the
trends view. Tell me which matter most.
