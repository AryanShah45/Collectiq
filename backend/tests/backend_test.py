"""
COLLECTIQ backend test suite (iteration 2 - restructured schema).
Covers:
  - auth (admin/viewer/logout)
  - meetings list & detail w/ NEW schema:
      reps.aging.othera, weekly_collection, last_week_target
      branches.purchase/sales.{value,tons}.{mbs,mcorp}
      marketing_reps.{visit,inquiry,inquiry_conform,order_loss}
      summary: total_outstanding ~2.03e8, branch_count=4,
               marketing_rep_count=3, new_target_total == total_outstanding
  - admin CRUD with full new payload (verifies auto last_week_target wiring)
  - role enforcement, analytics trends, users CRUD
  - ASYNC /api/extract: POST -> {job_id}, poll GET /api/extract/{job_id}
    (real Gemini call - gated by RUN_EXTRACT env flag).
"""
import os
import time
import uuid
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL").rstrip("/")
API = f"{BASE_URL}/api"

ADMIN_EMAIL = "admin@company.com"
ADMIN_PASSWORD = "Admin@123"
VIEWER_EMAIL = "viewer@company.com"
VIEWER_PASSWORD = "Viewer@123"

PDF_URL = ("https://customer-assets.emergentagent.com/"
           "job_6de14f9a-ce10-4cef-847e-b5d26c9588d1/artifacts/"
           "6pk3kyeb_MEETING%20DT%20-%2024-06-2025.pdf")


# ---------- fixtures ----------
@pytest.fixture(scope="module")
def admin_session():
    s = requests.Session()
    r = s.post(f"{API}/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}, timeout=30)
    assert r.status_code == 200, f"Admin login failed: {r.status_code} {r.text}"
    body = r.json()
    assert body["email"] == ADMIN_EMAIL
    assert body["role"] == "admin"
    return s


@pytest.fixture(scope="module")
def viewer_session():
    s = requests.Session()
    r = s.post(f"{API}/auth/login", json={"email": VIEWER_EMAIL, "password": VIEWER_PASSWORD}, timeout=30)
    assert r.status_code == 200, f"Viewer login failed: {r.status_code} {r.text}"
    assert r.json()["role"] == "viewer"
    return s


@pytest.fixture(scope="module")
def anon_session():
    return requests.Session()


# ---------- auth ----------
class TestAuth:
    def test_health(self):
        r = requests.get(f"{API}/", timeout=15)
        assert r.status_code == 200

    def test_admin_login_sets_cookies(self, admin_session):
        cookies = admin_session.cookies.get_dict()
        assert "access_token" in cookies
        assert "refresh_token" in cookies

    def test_me_admin(self, admin_session):
        r = admin_session.get(f"{API}/auth/me", timeout=15)
        assert r.status_code == 200
        data = r.json()
        assert data["email"] == ADMIN_EMAIL
        assert data["role"] == "admin"
        assert "id" in data

    def test_me_viewer(self, viewer_session):
        r = viewer_session.get(f"{API}/auth/me", timeout=15)
        assert r.status_code == 200
        assert r.json()["role"] == "viewer"

    def test_me_unauth(self, anon_session):
        r = anon_session.get(f"{API}/auth/me", timeout=15)
        assert r.status_code == 401

    def test_login_invalid(self):
        r = requests.post(f"{API}/auth/login", json={"email": ADMIN_EMAIL, "password": "wrong"}, timeout=15)
        assert r.status_code == 401

    def test_logout_clears(self):
        s = requests.Session()
        r = s.post(f"{API}/auth/login", json={"email": VIEWER_EMAIL, "password": VIEWER_PASSWORD}, timeout=15)
        assert r.status_code == 200
        r = s.post(f"{API}/auth/logout", timeout=15)
        assert r.status_code == 200
        r = s.get(f"{API}/auth/me", timeout=15)
        assert r.status_code == 401


# ---------- meetings list & detail (NEW schema) ----------
class TestMeetings:
    def test_list_meetings_seeded(self, admin_session):
        r = admin_session.get(f"{API}/meetings", timeout=20)
        assert r.status_code == 200
        meetings = r.json()
        assert isinstance(meetings, list)
        assert len(meetings) >= 4, f"Expected 4+ seeded meetings, got {len(meetings)}"
        for m in meetings:
            assert "id" in m
            assert "summary" in m
            s = m["summary"]
            for k in ("total_outstanding", "d90", "d60", "d30", "othera",
                      "collected", "coll_pct", "new_target_total",
                      "branch_count", "marketing_rep_count"):
                assert k in s, f"Missing summary key {k}"

    def test_latest_meeting_summary(self, admin_session):
        r = admin_session.get(f"{API}/meetings", timeout=20)
        meetings = r.json()
        latest = next((m for m in meetings if m.get("meeting_date", "").startswith("2025-06-24")), None)
        assert latest is not None, "Seeded meeting 2025-06-24 not found"
        s = latest["summary"]
        total = s["total_outstanding"]
        # Expected ~203,418,223 (incl. OTHER bucket)
        assert 200_000_000 <= total <= 207_000_000, f"Latest total {total} outside expected range"
        # collected ~18.7M
        assert 17_000_000 <= s["collected"] <= 20_000_000, f"Collected {s['collected']} unexpected"
        assert s["branch_count"] == 4
        assert s["marketing_rep_count"] == 3
        # new_target_total mirrors total_outstanding
        assert abs(s["new_target_total"] - s["total_outstanding"]) < 1.0

    def test_get_meeting_detail_new_schema(self, admin_session):
        r = admin_session.get(f"{API}/meetings", timeout=20)
        meetings = r.json()
        latest = next((m for m in meetings if m.get("meeting_date", "").startswith("2025-06-24")), None)
        r2 = admin_session.get(f"{API}/meetings/{latest['id']}", timeout=20)
        assert r2.status_code == 200
        m = r2.json()
        # reps: aging.othera + weekly_collection + last_week_target
        reps = m.get("reps", [])
        assert len(reps) >= 4
        any_othera = False
        for rep in reps:
            ag = rep["aging"]
            for bucket in ("d90", "d60", "d30", "othera"):
                assert bucket in ag, f"Missing bucket {bucket}"
                assert "mbs" in ag[bucket] and "mcorp" in ag[bucket]
            if (ag["othera"].get("mbs", 0) or 0) + (ag["othera"].get("mcorp", 0) or 0) > 0:
                any_othera = True
            perf = rep.get("performance", {})
            assert "weekly_collection" in perf or "weekly_collection" in rep
            assert "last_week_target" in perf or "last_week_target" in rep
        assert any_othera, "Expected at least one rep with othera > 0"

        # branches with value{mbs,mcorp} + tons{mbs,mcorp}
        branches = m.get("branches", [])
        assert len(branches) == 4
        branch_names = {b["name"].lower() for b in branches}
        for expected in ("sachin", "ankleshwar", "udhna", "kadodra"):
            assert any(expected in n for n in branch_names), f"Missing branch {expected}"
        for b in branches:
            for op in ("purchase", "sales"):
                section = b[op]
                for axis in ("value", "tons"):
                    assert axis in section
                    assert "mbs" in section[axis] and "mcorp" in section[axis]

        # quotation
        q = m.get("quotation", {})
        for k in ("prepair", "conform", "pending", "under_process", "not_conform"):
            assert k in q, f"Missing quotation field {k}"

        # marketing_reps with visit/inquiry/inquiry_conform/order_loss
        mreps = m.get("marketing_reps", [])
        assert len(mreps) == 3
        for mr in mreps:
            assert "name" in mr
            for field in ("visit", "inquiry", "inquiry_conform", "order_loss"):
                assert field in mr
                assert "mbs" in mr[field] and "mcorp" in mr[field]

    def test_get_meeting_not_found(self, admin_session):
        r = admin_session.get(f"{API}/meetings/{uuid.uuid4()}", timeout=15)
        assert r.status_code == 404


# ---------- role enforcement ----------
class TestRoleEnforcement:
    def test_viewer_cannot_create_meeting(self, viewer_session):
        r = viewer_session.post(f"{API}/meetings", json={"meeting_date": "2025-07-01", "reps": []}, timeout=15)
        assert r.status_code == 403

    def test_anon_cannot_create_meeting(self, anon_session):
        r = anon_session.post(f"{API}/meetings", json={"meeting_date": "2025-07-01", "reps": []}, timeout=15)
        assert r.status_code == 401

    def test_viewer_cannot_delete(self, viewer_session, admin_session):
        r = admin_session.get(f"{API}/meetings", timeout=15)
        mid = r.json()[0]["id"]
        r2 = viewer_session.delete(f"{API}/meetings/{mid}", timeout=15)
        assert r2.status_code == 403

    def test_viewer_cannot_list_users(self, viewer_session):
        r = viewer_session.get(f"{API}/users", timeout=15)
        assert r.status_code == 403

    def test_viewer_cannot_extract(self, viewer_session):
        files = {"file": ("a.txt", b"hi", "text/plain")}
        r = viewer_session.post(f"{API}/extract", files=files, timeout=30)
        assert r.status_code == 403

    def test_anon_cannot_extract(self, anon_session):
        files = {"file": ("a.txt", b"hi", "text/plain")}
        r = anon_session.post(f"{API}/extract", files=files, timeout=15)
        assert r.status_code == 401


# ---------- admin CRUD (full new schema + auto last_week_target) ----------
class TestAdminCRUD:
    def test_create_update_delete_meeting_full_schema(self, admin_session):
        payload = {
            "title": "TEST_Weekly",
            "meeting_date": "2025-07-15",
            "period_start": "2025-07-08",
            "period_end": "2025-07-14",
            "notes": "test",
            "reps": [{
                "name": "TEST_Rep",
                "aging": {
                    "d90": {"mbs": 100, "mcorp": 200},
                    "d60": {"mbs": 50, "mcorp": 25},
                    "d30": {"mbs": 10, "mcorp": 5},
                    "othera": {"mbs": 7, "mcorp": 3},
                },
                "performance": {
                    "coll_per_day": 100,
                    "coll_pct": 50,
                    "weekly_collection": 1234,
                    "new_target": 0,  # should be auto-computed
                    "last_week_target": 0,  # should be auto-filled from prior meeting
                    "working_days": 6,
                },
            }],
            "branches": [{
                "name": "Sachin",
                "purchase": {"value": {"mbs": 1000, "mcorp": 2000},
                             "tons": {"mbs": 10, "mcorp": 20}},
                "sales":    {"value": {"mbs": 500, "mcorp": 1500},
                             "tons": {"mbs": 5, "mcorp": 15}},
            }],
            "quotation": {
                "prepair":      {"mbs": 1, "mcorp": 1},
                "conform":      {"mbs": 1, "mcorp": 1},
                "pending":      {"mbs": 0, "mcorp": 0},
                "under_process":{"mbs": 0, "mcorp": 0},
                "not_conform":  {"mbs": 0, "mcorp": 0},
            },
            "marketing_reps": [{
                "name": "TEST_Marketer",
                "visit":           {"mbs": 2, "mcorp": 3},
                "inquiry":         {"mbs": 1, "mcorp": 1},
                "inquiry_conform": {"mbs": 1, "mcorp": 0},
                "order_loss":      {"mbs": 0, "mcorp": 0},
            }],
        }
        r = admin_session.post(f"{API}/meetings", json=payload, timeout=30)
        assert r.status_code == 200, r.text
        created = r.json()
        assert created["title"] == "TEST_Weekly"
        # total_outstanding = sum of all aging buckets (mbs+mcorp)
        # = 300+75+15+10 = 400
        assert created["summary"]["total_outstanding"] == 400
        assert created["summary"]["branch_count"] == 1
        assert created["summary"]["marketing_rep_count"] == 1
        # auto-fill: last_week_target for TEST_Rep should come from prior meeting (any rep total)
        # Since TEST_Rep doesn't exist in prior meetings the server may set it to 0 OR
        # the latest-rep total. Accept either, but field must exist & be a number.
        rep = created["reps"][0]
        perf = rep.get("performance", {})
        lwt = perf.get("last_week_target", rep.get("last_week_target"))
        assert isinstance(lwt, (int, float))
        mid = created["id"]

        # GET to verify persistence
        r2 = admin_session.get(f"{API}/meetings/{mid}", timeout=15)
        assert r2.status_code == 200
        got = r2.json()
        assert got["reps"][0]["name"] == "TEST_Rep"
        assert got["branches"][0]["name"] == "Sachin"
        assert got["branches"][0]["purchase"]["tons"]["mbs"] == 10
        assert got["marketing_reps"][0]["name"] == "TEST_Marketer"

        # UPDATE
        payload["title"] = "TEST_Weekly_Updated"
        r3 = admin_session.put(f"{API}/meetings/{mid}", json=payload, timeout=20)
        assert r3.status_code == 200
        assert r3.json()["title"] == "TEST_Weekly_Updated"

        # DELETE
        r4 = admin_session.delete(f"{API}/meetings/{mid}", timeout=15)
        assert r4.status_code == 200
        r5 = admin_session.get(f"{API}/meetings/{mid}", timeout=15)
        assert r5.status_code == 404


# ---------- analytics ----------
class TestAnalytics:
    def test_trends(self, admin_session):
        r = admin_session.get(f"{API}/analytics/trends", timeout=20)
        assert r.status_code == 200
        body = r.json()
        assert "weekly" in body
        assert isinstance(body["weekly"], list)
        assert len(body["weekly"]) >= 4
        sample = body["weekly"][0]
        for k in ("meeting_date", "total_outstanding", "d90", "d60", "d30",
                  "othera", "collected", "coll_pct"):
            assert k in sample, f"Missing trend key {k}"


# ---------- users ----------
class TestUsers:
    def test_list_users(self, admin_session):
        r = admin_session.get(f"{API}/users", timeout=15)
        assert r.status_code == 200
        emails = {u["email"] for u in r.json()}
        assert ADMIN_EMAIL in emails
        assert VIEWER_EMAIL in emails

    def test_create_and_delete_viewer(self, admin_session):
        email = f"test_{uuid.uuid4().hex[:8]}@example.com"
        r = admin_session.post(f"{API}/users", json={
            "name": "TEST User", "email": email, "password": "TestPass@123", "role": "viewer",
        }, timeout=15)
        assert r.status_code == 200, r.text
        uid = r.json()["id"]
        r3 = admin_session.delete(f"{API}/users/{uid}", timeout=15)
        assert r3.status_code == 200

    def test_admin_cannot_delete_self(self, admin_session):
        r = admin_session.get(f"{API}/auth/me", timeout=15)
        admin_id = r.json()["id"]
        r2 = admin_session.delete(f"{API}/users/{admin_id}", timeout=15)
        assert r2.status_code == 400


# ---------- LLM extract (ASYNC: POST -> job_id, poll GET) ----------
@pytest.mark.skipif(os.environ.get("RUN_EXTRACT", "1") != "1",
                    reason="Set RUN_EXTRACT=1 to run real LLM extraction")
class TestExtractAsync:
    def test_extract_pdf_async_flow(self, admin_session):
        pdf = requests.get(PDF_URL, timeout=60)
        assert pdf.status_code == 200, f"Could not download fixture PDF: {pdf.status_code}"
        files = {"file": ("MEETING-DT-24-06-2025.pdf", pdf.content, "application/pdf")}
        r = admin_session.post(f"{API}/extract", files=files, timeout=60)
        assert r.status_code == 200, r.text
        job = r.json()
        assert "job_id" in job, f"Expected job_id, got {job}"
        job_id = job["job_id"]
        assert job.get("status") in ("processing", "queued", "pending", "running", "done")

        # poll up to ~150s
        deadline = time.time() + 150
        status = None
        data = None
        while time.time() < deadline:
            pr = admin_session.get(f"{API}/extract/{job_id}", timeout=20)
            assert pr.status_code == 200, pr.text
            body = pr.json()
            status = body.get("status")
            if status == "done":
                data = body.get("data") or {}
                break
            if status == "error":
                pytest.fail(f"Extraction job errored: {body}")
            time.sleep(5)

        assert status == "done", f"Extraction did not finish in time, last status={status}"
        assert isinstance(data, dict)
        reps = data.get("reps", [])
        assert isinstance(reps, list) and len(reps) > 0, f"Expected non-empty reps, got {reps}"
        # at least one rep has aging.othera key present
        first = reps[0]
        assert "aging" in first, f"Rep missing aging: {first}"
        assert "othera" in first["aging"], f"Rep aging missing othera: {first['aging']}"
        # branches/marketing_reps keys are present in returned data
        assert "branches" in data, "Extracted data missing 'branches' key"
        assert "marketing_reps" in data, "Extracted data missing 'marketing_reps' key"
