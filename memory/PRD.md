# COLLECTIQ — Collection Intelligence Dashboard (PRD)

## Original Problem Statement
Build a "Meeting Insight" web app that automates the company's **weekly Collection Outstanding meeting** (currently a dense PDF: "MEETING DT - 24-06-2025"). It must present accounts-receivable aging buckets (90 / 60 / 30 days) per sales representative, split across **two separate companies (MBS & MCORP)**, plus performance metrics, targets, and a quotation pipeline — in a structured, analytical way with a complete overview of insights.

## User Choices
1. Data entry: **both** manual forms + PDF/Excel auto-extraction
2. Aging buckets: **90 / 60 / 30 days** (as in the PDF)
3. MBS & MCORP = **two separate companies**
4. Store **full history** with **weekly + monthly trends**
5. **Login with roles** — admin enters data, viewers read-only

## Architecture
- **Backend**: FastAPI + MongoDB (motor). Modules: `db.py`, `auth.py` (cookie JWT + roles + brute force + seeding), `routes_meetings.py` (meetings CRUD, analytics, async extract jobs), `extraction.py` (Gemini 2.5 Pro via emergentintegrations / Emergent universal key), `seed_data.py`.
- **Frontend**: React (CRA + craco), Tailwind, shadcn/ui, Recharts, framer-motion, react-query, react-router. IBM Plex Sans/Mono, Swiss high-contrast light theme.
- **Auth**: httpOnly cookie JWT, roles `admin`/`viewer`. Admin seeded from env; viewer demo seeded.

## User Personas
- **Admin / Manager**: records weekly numbers (manual or PDF upload), manages users.
- **Viewer / Leadership**: reads dashboards, trends, leaderboards in meetings.

## Core Requirements (static)
- Aging analysis 90/60/30 by rep and by company (MBS vs MCORP).
- KPIs, rep leaderboard, quotation pipeline funnel, auto insight alerts.
- Weekly + monthly trends over history.
- PDF/Excel AI extraction with review-before-save.
- Role-based access.

## Implemented (2026-06-25)
- ✅ Cookie JWT auth, roles, seeded admin + viewer, user management (admin).
- ✅ **Restructured data model**: per collection-rep aging **90/60/30 + OTHER**, each with **MBS, MCORP & Total**; **New Target = total outstanding** (90+60+30+Other, both companies, auto-computed); **weekly collection** amount + Coll/Day + Coll%; `last_week_target` auto-derived from the prior week's rep total.
- ✅ **Branch-wise Sales & Purchase** (Sachin, Ankleshwar, Udhna, Kadodra) in **both ₹ value and Tons**, split MBS/MCORP; add/remove branches.
- ✅ **Marketing section**: quotation pipeline + per-person activity (Visit, Inquiry, Inquiry Confirmed, Order Loss); add/remove marketing people.
- ✅ Add/remove flexibility for collection reps, branches AND marketing people.
- ✅ Seeded 4 weeks with real PDF numbers (incl. OTHER bucket) + branches + marketing for instant trends.
- ✅ Tabbed Dashboard: **Collection & Aging** (detailed MBS/MCORP/Total table, aging chart, leaderboard, insights), **Sales & Purchase** (₹/Tons toggle, chart + table), **Marketing** (funnel + activity table). KPIs: Total Outstanding, 90-Day Overdue, Collected This Week, Collection %.
- ✅ Trends (weekly/monthly, company filter), Meetings archive, async AI PDF/Excel extraction (background job + polling).
- ✅ Tested twice: iteration_1 (22 checks) and iteration_2 after restructure — **backend 23/23 incl. real Gemini async extract, frontend 100%**. extract_jobs now auto-expire (TTL 24h).

## Backlog / Next
- **P1**: Export/share a meeting view (PDF or link) to circulate before the meeting.
- **P1**: Per-rep & per-branch drill-down history pages.
- **P2**: Email/Slack weekly digest of insights.
- **P2**: Production hardening — cookie `secure=True` behind HTTPS; email-based lockout + per-IP ceiling (k8s ingress collapses client IPs).
- **P3**: Recharts width/height(-1) console warnings on tab switch (cosmetic).

## Credentials
See `/app/memory/test_credentials.md` (admin@company.com / Admin@123, viewer@company.com / Viewer@123).


---

## Changelog — Jul 2025 feature update

- **Aging**: added `d15` slab (MCORP only; MBS stays 0).
- **New Target** (per rep & totals) = d90+d60+d30 (MBS) + d90+d60+d30+d15 (MCORP). Excludes OTHER. `total_outstanding` includes d15+OTHER.
- **last_week_target**: now entered manually (no auto-derivation).
- **Per-day metrics**: Coll/Day and Sale/Day = value / 6 working days (fixed). Branch table has a Total row.
- **Direct Sale**: a normal branch entry.
- **Marketing**: kept Visit/Inquiry/Inq-Confirmed/Order-Loss; added per-branch sales (tons, MBS/MCORP), manual target_tons & target_party. Achieve
---

## Changelog — Jul 2025 feature update

- Aging: added d15 slab (MCORP only; MBS stays 0).
- New Target (per rep & totals) = d90+d60+d30 (MBS) + d90+d60+d30+d15 (MCORP). Excludes OTHER. total_outstanding includes d15+OTHER.
- last_week_target: now entered manually (no auto-derivation).
- Per-day metrics: Coll/Day and Sale/Day = value / 6 working days (fixed). Branch table has a Total row.
- Direct Sale: a normal branch entry.
- Marketing: kept Visit/Inquiry/Inq-Confirmed/Order-Loss; added per-branch sales (tons, MBS/MCORP), manual target_tons & target_party. Achieve%/Tons = total sales (both companies, all branches) / target_tons; Achieve%/Party = total visits / target_party (computed client-side).
- Auth: login page removed; app auto-signs-in as admin (retry-with-backoff).
