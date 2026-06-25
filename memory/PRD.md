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
- ✅ Meeting model (reps → aging d90/d60/d30/othera × MBS/MCORP, performance, quotation). CRUD with role enforcement.
- ✅ Seeded 4 weekly meetings (real PDF numbers for 24-06-2025 + 3 historical for trends).
- ✅ Dashboard: 4 KPI cards, aging stacked bar + composition pie, rep leaderboard, quotation funnel, smart insights, company toggle (All/MBS/MCORP), week selector.
- ✅ Trends page: outstanding-by-bucket area, collection-efficiency line, outstanding-vs-target line; weekly/monthly + company toggles.
- ✅ Meetings archive (list/view/edit/delete).
- ✅ Data Entry: manual form (date pickers, dynamic reps, quotation, live total) + **async AI PDF/Excel upload** (background job + polling, immune to gateway timeouts).
- ✅ Tested: 21/22 backend (extract now async-verified end-to-end), 100% frontend flows.

## Backlog / Next
- **P1**: Export dashboard/meeting as PDF or shareable link for circulating before meetings.
- **P1**: Per-rep drill-down page (history of a single rep's outstanding & collection %).
- **P2**: Email/Slack digest of the weekly insights.
- **P2**: Production hardening — set cookie `secure=True` behind HTTPS, lockout by email + per-IP ceiling (X-Forwarded-For aware).
- **P2**: Editable company/branch labels (Sachin, Udhna, Kadodra, Ankleshwar) + Direct Sale section.
- **P3**: Recharts width/height(-1) console warnings (cosmetic) — add explicit min-height to chart wrappers.

## Credentials
See `/app/memory/test_credentials.md` (admin@company.com / Admin@123, viewer@company.com / Viewer@123).
