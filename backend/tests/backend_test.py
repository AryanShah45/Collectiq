"""
COLLECTIQ backend test suite.
Covers: auth (admin/viewer/logout), meetings CRUD, analytics trends,
role enforcement, user management, and the LLM /api/extract endpoint
(real Gemini call - runs ONCE, gated by RUN_EXTRACT env flag).
"""
import os
import io
import uuid
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://collections-insights.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"

ADMIN_EMAIL = "admin@company.com"
ADMIN_PASSWORD = "Admin@123"
VIEWER_EMAIL = "viewer@company.com"
VIEWER_PASSWORD = "Viewer@123"

PDF_URL = "https://customer-assets.emergentagent.com/job_6de14f9a-ce10-4cef-847e-b5d26c9588d1/artifacts/6pk3kyeb_MEETING%20DT%20-%2024-06-2025.pdf"


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
    body = r.json()
    assert body["role"] == "viewer"
    return s


@pytest.fixture(scope="module")
def anon_session():
    return requests.Session()


# ---------- auth ----------
class TestAuth:
    def test_health(self):
        r = requests.get(f"{API}/", timeout=15)
        assert r.status_code == 200
        assert "running" in r.json().get("message", "").lower()

    def test_admin_login_sets_cookies(self, admin_session):
        # cookies should be set on the session
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
        # subsequent /me must be 401
        r = s.get(f"{API}/auth/me", timeout=15)
        assert r.status_code == 401


# ---------- meetings list & detail ----------
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
            for k in ("total_outstanding", "d90", "d60", "d30", "avg_coll_pct", "total_new_target"):
                assert k in s, f"Missing summary key {k}"

    def test_latest_meeting_total(self, admin_session):
        r = admin_session.get(f"{API}/meetings", timeout=20)
        meetings = r.json()
        # find 2025-06-24
        latest = next((m for m in meetings if m.get("meeting_date", "").startswith("2025-06-24")), None)
        assert latest is not None, "Seeded meeting 2025-06-24 not found"
        total = latest["summary"]["total_outstanding"]
        # approx ~112167609
        assert 110_000_000 <= total <= 115_000_000, f"Latest total {total} outside expected range"

    def test_get_meeting_detail(self, admin_session):
        r = admin_session.get(f"{API}/meetings", timeout=20)
        meetings = r.json()
        first = meetings[0]
        r2 = admin_session.get(f"{API}/meetings/{first['id']}", timeout=20)
        assert r2.status_code == 200
        m = r2.json()
        reps = m.get("reps", [])
        assert len(reps) == 5, f"Expected 5 reps, got {len(reps)}"
        rep_names = {rep["name"] for rep in reps}
        # accept partial matches just in case (case-insensitive contains)
        expected = ["Arun", "Ghanshyam", "Kamlesh", "Ankleshwar", "Umeshbhai"]
        for name in expected:
            found = any(name.lower() in rn.lower() for rn in rep_names)
            assert found, f"Rep {name} not found in {rep_names}"
        # aging buckets
        for rep in reps:
            ag = rep["aging"]
            for bucket in ("d90", "d60", "d30"):
                assert "mbs" in ag[bucket]
                assert "mcorp" in ag[bucket]

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


# ---------- admin CRUD ----------
class TestAdminCRUD:
    def test_create_update_delete_meeting(self, admin_session):
        payload = {
            "title": "TEST_Weekly",
            "meeting_date": "2025-07-08",
            "period_start": "2025-07-01",
            "period_end": "2025-07-07",
            "notes": "test",
            "reps": [{
                "name": "TEST_Rep",
                "aging": {"d90": {"mbs": 100, "mcorp": 200},
                          "d60": {"mbs": 50, "mcorp": 25},
                          "d30": {"mbs": 10, "mcorp": 5},
                          "othera": {"mbs": 0, "mcorp": 0}},
                "performance": {"coll_per_day": 100, "coll_pct": 50,
                                "new_target": 1000, "last_week_target": 800,
                                "purchase": {"mbs": 0, "mcorp": 0},
                                "sales": {"mbs": 0, "mcorp": 0}},
            }],
            "quotation": {},
        }
        r = admin_session.post(f"{API}/meetings", json=payload, timeout=20)
        assert r.status_code == 200, r.text
        created = r.json()
        assert created["title"] == "TEST_Weekly"
        assert created["summary"]["total_outstanding"] == 390
        mid = created["id"]

        # GET to verify persistence
        r2 = admin_session.get(f"{API}/meetings/{mid}", timeout=15)
        assert r2.status_code == 200
        assert r2.json()["reps"][0]["name"] == "TEST_Rep"

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
        assert "weekly" in body and "monthly" in body
        assert isinstance(body["weekly"], list) and isinstance(body["monthly"], list)
        assert len(body["weekly"]) >= 4
        sample = body["weekly"][0]
        for k in ("meeting_date", "total_outstanding", "d90", "d60", "d30", "avg_coll_pct"):
            assert k in sample


# ---------- users ----------
class TestUsers:
    def test_list_users(self, admin_session):
        r = admin_session.get(f"{API}/users", timeout=15)
        assert r.status_code == 200
        users = r.json()
        emails = {u["email"] for u in users}
        assert ADMIN_EMAIL in emails
        assert VIEWER_EMAIL in emails

    def test_create_and_delete_viewer(self, admin_session):
        email = f"test_{uuid.uuid4().hex[:8]}@example.com"
        r = admin_session.post(f"{API}/users", json={
            "name": "TEST User", "email": email, "password": "TestPass@123", "role": "viewer",
        }, timeout=15)
        assert r.status_code == 200, r.text
        created = r.json()
        assert created["email"] == email
        assert created["role"] == "viewer"
        uid = created["id"]
        # verify list
        r2 = admin_session.get(f"{API}/users", timeout=15)
        assert any(u["email"] == email for u in r2.json())
        # delete
        r3 = admin_session.delete(f"{API}/users/{uid}", timeout=15)
        assert r3.status_code == 200

    def test_admin_cannot_delete_self(self, admin_session):
        r = admin_session.get(f"{API}/auth/me", timeout=15)
        admin_id = r.json()["id"]
        r2 = admin_session.delete(f"{API}/users/{admin_id}", timeout=15)
        assert r2.status_code == 400


# ---------- LLM extract (real, runs once) ----------
@pytest.mark.skipif(os.environ.get("RUN_EXTRACT", "1") != "1",
                    reason="Set RUN_EXTRACT=1 to run real LLM extraction")
class TestExtract:
    def test_extract_real_pdf(self, admin_session):
        # download PDF
        pdf = requests.get(PDF_URL, timeout=60)
        assert pdf.status_code == 200
        files = {"file": ("MEETING-DT-24-06-2025.pdf", pdf.content, "application/pdf")}
        r = admin_session.post(f"{API}/extract", files=files, timeout=180)
        assert r.status_code == 200, r.text
        body = r.json()
        assert body.get("ok") is True
        data = body.get("data", {})
        reps = data.get("reps", [])
        assert isinstance(reps, list) and len(reps) > 0, f"Expected non-empty reps, got {reps}"
        # at least one rep has a name
        assert any(rep.get("name") for rep in reps)
