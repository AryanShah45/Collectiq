"""
CollectIQ Backend Test - Data Model & Calculation Changes (d15 slab, manual last_week_target)

Tests the new feature requirements:
1. d15 aging slab (MCORP only) in rep.aging
2. summary.new_target_total = d90+d60+d30+d15 (EXCLUDES othera)
3. summary.total_outstanding = d90+d60+d30+d15+othera (INCLUDES othera)
4. Manual last_week_target preservation (NOT auto-derived)
5. Direct Sale branch persistence
6. Marketing branch_sales with target_tons/target_party
"""
import os
import requests

# Configuration
BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://github-app-opener-1.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"
ADMIN_EMAIL = "admin@company.com"
ADMIN_PASSWORD = "Admin@123"

# Test state
created_meeting_id = None


def login():
    """Login as admin and return session with cookies."""
    session = requests.Session()
    r = session.post(f"{API}/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}, timeout=30)
    assert r.status_code == 200, f"❌ Login failed: {r.status_code} {r.text}"
    body = r.json()
    assert body["email"] == ADMIN_EMAIL, f"❌ Email mismatch: {body.get('email')}"
    assert body["role"] == "admin", f"❌ Role mismatch: {body.get('role')}"
    print(f"✅ Logged in as {ADMIN_EMAIL}")
    return session


def test_get_meetings_d15_and_summary(session):
    """
    Test 1: GET /api/meetings
    - Each rep has aging.d15 with {mbs: 0, mcorp: positive}
    - Each meeting has summary.d15
    - summary.new_target_total = d90+d60+d30+d15 (excludes othera)
    - summary.total_outstanding = d90+d60+d30+d15+othera
    - Branches include "Direct Sale"
    - Marketing reps have branch_sales array with target_tons/target_party
    """
    print("\n=== TEST 1: GET /api/meetings - d15 slab & summary calculations ===")
    r = session.get(f"{API}/meetings", timeout=30)
    assert r.status_code == 200, f"❌ GET /api/meetings failed: {r.status_code} {r.text}"
    
    meetings = r.json()
    assert isinstance(meetings, list), f"❌ Expected list, got {type(meetings)}"
    assert len(meetings) >= 4, f"❌ Expected at least 4 meetings, got {len(meetings)}"
    print(f"✅ Retrieved {len(meetings)} meetings")
    
    # Test the latest meeting (2025-06-24)
    latest = next((m for m in meetings if m.get("meeting_date", "").startswith("2025-06-24")), None)
    assert latest is not None, "❌ Latest meeting (2025-06-24) not found"
    print(f"✅ Found latest meeting: {latest['meeting_date']}")
    
    # Check reps have d15 slab
    reps = latest.get("reps", [])
    assert len(reps) >= 5, f"❌ Expected at least 5 reps, got {len(reps)}"
    
    d15_found = False
    for rep in reps:
        aging = rep.get("aging", {})
        assert "d15" in aging, f"❌ Rep {rep.get('name')} missing d15 in aging"
        d15 = aging["d15"]
        assert "mbs" in d15 and "mcorp" in d15, f"❌ d15 missing mbs/mcorp: {d15}"
        assert d15["mbs"] == 0, f"❌ d15.mbs should be 0 (MCORP only), got {d15['mbs']}"
        if d15["mcorp"] > 0:
            d15_found = True
            print(f"  ✅ Rep '{rep['name']}' has d15: mbs={d15['mbs']}, mcorp={d15['mcorp']}")
    
    assert d15_found, "❌ No rep has d15.mcorp > 0"
    
    # Check summary has d15
    summary = latest.get("summary", {})
    assert "d15" in summary, "❌ summary missing d15"
    print(f"  ✅ summary.d15 = {summary['d15']}")
    
    # Verify new_target_total calculation (excludes othera, includes d15)
    d90 = summary.get("d90", 0)
    d60 = summary.get("d60", 0)
    d30 = summary.get("d30", 0)
    d15 = summary.get("d15", 0)
    othera = summary.get("othera", 0)
    new_target_total = summary.get("new_target_total", 0)
    total_outstanding = summary.get("total_outstanding", 0)
    
    expected_new_target = d90 + d60 + d30 + d15
    expected_total_outstanding = d90 + d60 + d30 + d15 + othera
    
    print(f"  Summary breakdown:")
    print(f"    d90={d90}, d60={d60}, d30={d30}, d15={d15}, othera={othera}")
    print(f"    new_target_total={new_target_total} (expected: {expected_new_target})")
    print(f"    total_outstanding={total_outstanding} (expected: {expected_total_outstanding})")
    
    assert abs(new_target_total - expected_new_target) < 0.1, \
        f"❌ new_target_total mismatch: {new_target_total} != {expected_new_target}"
    print(f"  ✅ new_target_total = d90+d60+d30+d15 = {new_target_total} (EXCLUDES othera)")
    
    assert abs(total_outstanding - expected_total_outstanding) < 0.1, \
        f"❌ total_outstanding mismatch: {total_outstanding} != {expected_total_outstanding}"
    print(f"  ✅ total_outstanding = d90+d60+d30+d15+othera = {total_outstanding}")
    
    # Verify othera is NOT in new_target_total
    assert new_target_total < total_outstanding, \
        f"❌ new_target_total should be LESS than total_outstanding (othera excluded)"
    print(f"  ✅ Confirmed: new_target_total ({new_target_total}) < total_outstanding ({total_outstanding})")
    
    # Check for Direct Sale branch
    branches = latest.get("branches", [])
    branch_names = [b.get("name", "").lower() for b in branches]
    assert any("direct sale" in name for name in branch_names), \
        f"❌ 'Direct Sale' branch not found. Branches: {branch_names}"
    print(f"  ✅ Found 'Direct Sale' branch in {len(branches)} branches")
    
    # Check marketing_reps have branch_sales, target_tons, target_party
    marketing_reps = latest.get("marketing_reps", [])
    assert len(marketing_reps) >= 3, f"❌ Expected at least 3 marketing reps, got {len(marketing_reps)}"
    
    for mrep in marketing_reps:
        name = mrep.get("name", "")
        assert "branch_sales" in mrep, f"❌ Marketing rep '{name}' missing branch_sales"
        assert "target_tons" in mrep, f"❌ Marketing rep '{name}' missing target_tons"
        assert "target_party" in mrep, f"❌ Marketing rep '{name}' missing target_party"
        
        branch_sales = mrep["branch_sales"]
        assert isinstance(branch_sales, list), f"❌ branch_sales should be list, got {type(branch_sales)}"
        
        if len(branch_sales) > 0:
            bs = branch_sales[0]
            assert "name" in bs, f"❌ branch_sales item missing 'name'"
            assert "tons" in bs, f"❌ branch_sales item missing 'tons'"
            tons = bs["tons"]
            assert "mbs" in tons and "mcorp" in tons, f"❌ tons missing mbs/mcorp"
            print(f"  ✅ Marketing rep '{name}': branch_sales={len(branch_sales)}, target_tons={mrep['target_tons']}, target_party={mrep['target_party']}")
    
    print("✅ TEST 1 PASSED: GET /api/meetings verified")


def test_create_meeting_with_d15_and_manual_target(session):
    """
    Test 2: POST /api/meetings - Create meeting with:
    - Rep with d15 (mcorp only)
    - Direct Sale branch
    - Marketing rep with branch_sales, target_tons, target_party
    - Manual last_week_target (should NOT be overwritten)
    
    Then GET it back and verify all fields persisted.
    """
    global created_meeting_id
    
    print("\n=== TEST 2: POST /api/meetings - Create with d15, Direct Sale, manual last_week_target ===")
    
    payload = {
        "title": "TEST Meeting - d15 Verification",
        "meeting_date": "2025-07-04",
        "period_start": "2025-06-28",
        "period_end": "2025-07-04",
        "notes": "Test meeting for d15 slab and manual last_week_target",
        "reps": [{
            "name": "TestRep",
            "aging": {
                "d90": {"mbs": 1000, "mcorp": 100},
                "d60": {"mbs": 500, "mcorp": 50},
                "d30": {"mbs": 300, "mcorp": 30},
                "d15": {"mbs": 0, "mcorp": 25},  # d15 MCORP only
                "othera": {"mbs": 9999, "mcorp": 8888}
            },
            "weekly_collection": {"mbs": 200, "mcorp": 20},
            "last_week_target": 123456,  # Manual value - should NOT be overwritten
            "working_days": 6
        }],
        "branches": [
            {
                "name": "Direct Sale",
                "purchase": {
                    "tons": {"mbs": 10, "mcorp": 5},
                    "value": {"mbs": 0, "mcorp": 0}
                },
                "sales": {
                    "tons": {"mbs": 20, "mcorp": 8},
                    "value": {"mbs": 0, "mcorp": 0}
                }
            }
        ],
        "quotation": {
            "prepair": {"mbs": 1, "mcorp": 1},
            "conform": {"mbs": 1, "mcorp": 1},
            "pending": {"mbs": 0, "mcorp": 0},
            "under_process": {"mbs": 0, "mcorp": 0},
            "not_conform": {"mbs": 0, "mcorp": 0}
        },
        "marketing_reps": [{
            "name": "MktTest",
            "visit": {"mbs": 10, "mcorp": 5},
            "inquiry": {"mbs": 2, "mcorp": 1},
            "inquiry_conform": {"mbs": 1, "mcorp": 1},
            "order_loss": {"mbs": 0, "mcorp": 0},
            "branch_sales": [
                {"name": "Sachin", "tons": {"mbs": 12, "mcorp": 3}}
            ],
            "target_tons": 40,
            "target_party": 30
        }],
        "financials": {
            "sales_value": {"mbs": 0, "mcorp": 0},
            "purchase_value": {"mbs": 0, "mcorp": 0}
        }
    }
    
    print("  Creating meeting...")
    r = session.post(f"{API}/meetings", json=payload, timeout=30)
    assert r.status_code == 200, f"❌ POST /api/meetings failed: {r.status_code} {r.text}"
    
    created = r.json()
    created_meeting_id = created.get("id")
    assert created_meeting_id, "❌ No 'id' in created meeting response"
    print(f"  ✅ Created meeting with id: {created_meeting_id}")
    
    # Verify response has correct data
    rep = created["reps"][0]
    assert rep["name"] == "TestRep", f"❌ Rep name mismatch"
    assert rep["aging"]["d15"]["mcorp"] == 25, f"❌ d15.mcorp not persisted: {rep['aging']['d15']}"
    assert rep["aging"]["d15"]["mbs"] == 0, f"❌ d15.mbs should be 0"
    assert rep["last_week_target"] == 123456, \
        f"❌ last_week_target was overwritten! Expected 123456, got {rep['last_week_target']}"
    print(f"  ✅ Rep.aging.d15.mcorp = {rep['aging']['d15']['mcorp']}")
    print(f"  ✅ Rep.last_week_target = {rep['last_week_target']} (manual value preserved)")
    
    # Verify summary calculations
    summary = created["summary"]
    # new_target_total = 1000+100 + 500+50 + 300+30 + 0+25 = 2005 (excludes othera 9999+8888)
    expected_new_target = 1000 + 100 + 500 + 50 + 300 + 30 + 0 + 25
    assert summary["new_target_total"] == expected_new_target, \
        f"❌ new_target_total mismatch: {summary['new_target_total']} != {expected_new_target}"
    print(f"  ✅ summary.new_target_total = {summary['new_target_total']} (excludes othera)")
    
    # Verify othera is NOT in new_target_total
    total_outstanding = summary["total_outstanding"]
    assert total_outstanding > summary["new_target_total"], \
        f"❌ total_outstanding should be > new_target_total (othera included)"
    print(f"  ✅ summary.total_outstanding = {total_outstanding} (includes othera)")
    
    # Verify Direct Sale branch
    branches = created.get("branches", [])
    direct_sale = next((b for b in branches if "direct sale" in b["name"].lower()), None)
    assert direct_sale is not None, "❌ Direct Sale branch not found in response"
    assert direct_sale["purchase"]["tons"]["mbs"] == 10, "❌ Direct Sale purchase tons mismatch"
    assert direct_sale["sales"]["tons"]["mcorp"] == 8, "❌ Direct Sale sales tons mismatch"
    print(f"  ✅ Direct Sale branch persisted with correct tons")
    
    # Verify marketing rep
    mrep = created["marketing_reps"][0]
    assert mrep["name"] == "MktTest", "❌ Marketing rep name mismatch"
    assert mrep["target_tons"] == 40, f"❌ target_tons mismatch: {mrep['target_tons']}"
    assert mrep["target_party"] == 30, f"❌ target_party mismatch: {mrep['target_party']}"
    assert len(mrep["branch_sales"]) == 1, "❌ branch_sales count mismatch"
    bs = mrep["branch_sales"][0]
    assert bs["name"] == "Sachin", f"❌ branch_sales name mismatch: {bs['name']}"
    assert bs["tons"]["mbs"] == 12, f"❌ branch_sales tons.mbs mismatch: {bs['tons']['mbs']}"
    assert bs["tons"]["mcorp"] == 3, f"❌ branch_sales tons.mcorp mismatch: {bs['tons']['mcorp']}"
    print(f"  ✅ Marketing rep with branch_sales persisted correctly")
    
    # Now GET the meeting to verify persistence
    print(f"\n  Getting meeting {created_meeting_id} to verify persistence...")
    r2 = session.get(f"{API}/meetings/{created_meeting_id}", timeout=30)
    assert r2.status_code == 200, f"❌ GET /api/meetings/{created_meeting_id} failed: {r2.status_code}"
    
    retrieved = r2.json()
    rep2 = retrieved["reps"][0]
    assert rep2["aging"]["d15"]["mcorp"] == 25, \
        f"❌ d15.mcorp not persisted in DB: {rep2['aging']['d15']}"
    assert rep2["last_week_target"] == 123456, \
        f"❌ last_week_target changed after GET! Expected 123456, got {rep2['last_week_target']}"
    print(f"  ✅ GET verified: d15.mcorp={rep2['aging']['d15']['mcorp']}, last_week_target={rep2['last_week_target']}")
    
    print("✅ TEST 2 PASSED: POST /api/meetings verified")


def test_update_meeting_manual_target(session):
    """
    Test 3: PUT /api/meetings/{id} - Update last_week_target
    Verify the manual value persists (not auto-derived).
    """
    global created_meeting_id
    
    print("\n=== TEST 3: PUT /api/meetings/{id} - Update manual last_week_target ===")
    
    assert created_meeting_id, "❌ No meeting created in previous test"
    
    # Get current meeting
    r = session.get(f"{API}/meetings/{created_meeting_id}", timeout=30)
    assert r.status_code == 200, f"❌ GET failed: {r.status_code}"
    meeting = r.json()
    
    # Update last_week_target to 777
    meeting["reps"][0]["last_week_target"] = 777
    
    print(f"  Updating last_week_target to 777...")
    r2 = session.put(f"{API}/meetings/{created_meeting_id}", json=meeting, timeout=30)
    assert r2.status_code == 200, f"❌ PUT failed: {r2.status_code} {r2.text}"
    
    updated = r2.json()
    assert updated["reps"][0]["last_week_target"] == 777, \
        f"❌ last_week_target not updated: {updated['reps'][0]['last_week_target']}"
    print(f"  ✅ PUT response: last_week_target = {updated['reps'][0]['last_week_target']}")
    
    # GET again to verify persistence
    print(f"  Getting meeting again to verify persistence...")
    r3 = session.get(f"{API}/meetings/{created_meeting_id}", timeout=30)
    assert r3.status_code == 200, f"❌ GET failed: {r3.status_code}"
    
    retrieved = r3.json()
    assert retrieved["reps"][0]["last_week_target"] == 777, \
        f"❌ last_week_target not persisted: {retrieved['reps'][0]['last_week_target']}"
    print(f"  ✅ GET verified: last_week_target = {retrieved['reps'][0]['last_week_target']}")
    
    print("✅ TEST 3 PASSED: PUT /api/meetings verified")


def test_cleanup(session):
    """
    Test 4: DELETE /api/meetings/{id} - Cleanup test meeting
    """
    global created_meeting_id
    
    print("\n=== TEST 4: DELETE /api/meetings/{id} - Cleanup ===")
    
    assert created_meeting_id, "❌ No meeting to delete"
    
    print(f"  Deleting meeting {created_meeting_id}...")
    r = session.delete(f"{API}/meetings/{created_meeting_id}", timeout=30)
    assert r.status_code == 200, f"❌ DELETE failed: {r.status_code} {r.text}"
    print(f"  ✅ Meeting deleted")
    
    # Verify it's gone
    r2 = session.get(f"{API}/meetings/{created_meeting_id}", timeout=30)
    assert r2.status_code == 404, f"❌ Meeting still exists after delete: {r2.status_code}"
    print(f"  ✅ Verified: meeting no longer exists")
    
    print("✅ TEST 4 PASSED: DELETE /api/meetings verified")


def test_other_endpoints(session):
    """
    Test 5: Verify other endpoints still work
    - GET /api/auth/me
    - GET /api/settings
    - GET /api/analytics/trends
    """
    print("\n=== TEST 5: Other endpoints still working ===")
    
    # /api/auth/me
    r = session.get(f"{API}/auth/me", timeout=15)
    assert r.status_code == 200, f"❌ GET /api/auth/me failed: {r.status_code}"
    me = r.json()
    assert me["email"] == ADMIN_EMAIL, f"❌ /auth/me email mismatch"
    print(f"  ✅ GET /api/auth/me: {me['email']}")
    
    # /api/settings
    r = session.get(f"{API}/settings", timeout=15)
    assert r.status_code == 200, f"❌ GET /api/settings failed: {r.status_code}"
    settings = r.json()
    assert "company_a" in settings or "id" in settings, "❌ /settings response invalid"
    print(f"  ✅ GET /api/settings: OK")
    
    # /api/analytics/trends
    r = session.get(f"{API}/analytics/trends", timeout=20)
    assert r.status_code == 200, f"❌ GET /api/analytics/trends failed: {r.status_code}"
    trends = r.json()
    assert "weekly" in trends, "❌ /analytics/trends missing 'weekly'"
    assert len(trends["weekly"]) >= 4, f"❌ Expected at least 4 weeks, got {len(trends['weekly'])}"
    print(f"  ✅ GET /api/analytics/trends: {len(trends['weekly'])} weeks")
    
    print("✅ TEST 5 PASSED: Other endpoints verified")


def main():
    """Run all tests."""
    print("=" * 80)
    print("CollectIQ Backend Test - d15 Slab & Manual last_week_target")
    print("=" * 80)
    
    try:
        session = login()
        
        test_get_meetings_d15_and_summary(session)
        test_create_meeting_with_d15_and_manual_target(session)
        test_update_meeting_manual_target(session)
        test_cleanup(session)
        test_other_endpoints(session)
        
        print("\n" + "=" * 80)
        print("✅ ALL TESTS PASSED")
        print("=" * 80)
        
    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        raise
    except Exception as e:
        print(f"\n❌ UNEXPECTED ERROR: {e}")
        raise


if __name__ == "__main__":
    main()
