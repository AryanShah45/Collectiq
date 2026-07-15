#!/usr/bin/env python3
"""
Test Collection % formula change: (MBS+MCORP collected) ÷ last_week_target

Verifies:
1. GET /api/meetings - summary.last_week_target_total and coll_pct calculations
2. GET /api/analytics/trends - coll_pct uses last_week_target_total
3. GET /api/reps/Arun/history - per-rep coll_pct uses that rep's last_week_target
4. Round-trip POST/DELETE with specific test data
"""

import requests
import sys
from datetime import datetime

# Backend URL from frontend/.env
BASE_URL = "https://github-opener-9.preview.emergentagent.com/api"

# Test credentials from /app/memory/test_credentials.md
ADMIN_EMAIL = "admin@company.com"
ADMIN_PASSWORD = "Admin@123"

session = requests.Session()

def login():
    """Login as admin and establish session cookie."""
    print("\n=== AUTHENTICATION ===")
    resp = session.post(f"{BASE_URL}/auth/login", json={
        "email": ADMIN_EMAIL,
        "password": ADMIN_PASSWORD
    })
    print(f"POST /api/auth/login: {resp.status_code}")
    if resp.status_code != 200:
        print(f"ERROR: Login failed - {resp.text}")
        sys.exit(1)
    print(f"✓ Authenticated as {ADMIN_EMAIL}")
    return resp.json()

def test_meetings_endpoint():
    """
    Test 1: GET /api/meetings
    For every meeting m:
    - Compute sum_lwt = sum(rep.last_week_target for rep in m.reps)
    - Assert m.summary.last_week_target_total == round(sum_lwt, 2)
    - If sum_lwt > 0: assert m.summary.coll_pct == round(m.summary.collected * 100 / sum_lwt, 2)
    - If sum_lwt == 0: assert m.summary.coll_pct == 0
    - Confirm m.summary.new_target_total is present and equals d90+d60+d30+d15
    """
    print("\n=== TEST 1: GET /api/meetings ===")
    resp = session.get(f"{BASE_URL}/meetings")
    print(f"GET /api/meetings: {resp.status_code}")
    
    if resp.status_code != 200:
        print(f"ERROR: Failed to get meetings - {resp.text}")
        return False
    
    meetings = resp.json()
    print(f"Found {len(meetings)} meetings")
    
    all_passed = True
    for idx, m in enumerate(meetings):
        meeting_date = m.get("meeting_date", "unknown")
        print(f"\n  Meeting {idx+1}: {meeting_date}")
        
        # Compute sum_lwt
        sum_lwt = sum(rep.get("last_week_target", 0) for rep in m.get("reps", []))
        print(f"    Computed sum_lwt: {sum_lwt}")
        
        summary = m.get("summary", {})
        last_week_target_total = summary.get("last_week_target_total")
        coll_pct = summary.get("coll_pct")
        collected = summary.get("collected", 0)
        new_target_total = summary.get("new_target_total")
        
        print(f"    summary.last_week_target_total: {last_week_target_total}")
        print(f"    summary.collected: {collected}")
        print(f"    summary.coll_pct: {coll_pct}")
        print(f"    summary.new_target_total: {new_target_total}")
        
        # Check 1: last_week_target_total matches sum_lwt
        expected_lwt_total = round(sum_lwt, 2)
        if last_week_target_total != expected_lwt_total:
            print(f"    ❌ FAIL: last_week_target_total {last_week_target_total} != expected {expected_lwt_total}")
            all_passed = False
        else:
            print(f"    ✓ last_week_target_total matches sum_lwt")
        
        # Check 2: coll_pct calculation
        if sum_lwt > 0:
            expected_coll_pct = round(collected * 100 / sum_lwt, 2)
            if abs(coll_pct - expected_coll_pct) > 0.01:  # Allow small floating point difference
                print(f"    ❌ FAIL: coll_pct {coll_pct} != expected {expected_coll_pct}")
                all_passed = False
            else:
                print(f"    ✓ coll_pct calculation correct: {coll_pct}%")
        else:
            if coll_pct != 0:
                print(f"    ❌ FAIL: coll_pct should be 0 when sum_lwt is 0, got {coll_pct}")
                all_passed = False
            else:
                print(f"    ✓ coll_pct is 0 (sum_lwt is 0)")
        
        # Check 3: new_target_total is present and equals d90+d60+d30+d15
        d90 = summary.get("d90", 0)
        d60 = summary.get("d60", 0)
        d30 = summary.get("d30", 0)
        d15 = summary.get("d15", 0)
        expected_new_target = round(d90 + d60 + d30 + d15, 2)
        
        if new_target_total is None:
            print(f"    ❌ FAIL: new_target_total is missing")
            all_passed = False
        elif abs(new_target_total - expected_new_target) > 0.01:
            print(f"    ❌ FAIL: new_target_total {new_target_total} != expected {expected_new_target} (d90+d60+d30+d15)")
            all_passed = False
        else:
            print(f"    ✓ new_target_total correct: {new_target_total}")
    
    return all_passed

def test_trends_endpoint():
    """
    Test 2: GET /api/analytics/trends
    For each weekly point:
    - coll_pct derived from collected / last_week_target_total * 100
    - Verify last_week_target_total is present in each point
    """
    print("\n=== TEST 2: GET /api/analytics/trends ===")
    resp = session.get(f"{BASE_URL}/analytics/trends")
    print(f"GET /api/analytics/trends: {resp.status_code}")
    
    if resp.status_code != 200:
        print(f"ERROR: Failed to get trends - {resp.text}")
        return False
    
    data = resp.json()
    weekly = data.get("weekly", [])
    print(f"Found {len(weekly)} weekly points")
    
    all_passed = True
    for idx, point in enumerate(weekly):
        meeting_date = point.get("meeting_date", "unknown")
        print(f"\n  Point {idx+1}: {meeting_date}")
        
        last_week_target_total = point.get("last_week_target_total")
        coll_pct = point.get("coll_pct")
        collected = point.get("collected", 0)
        
        print(f"    last_week_target_total: {last_week_target_total}")
        print(f"    collected: {collected}")
        print(f"    coll_pct: {coll_pct}")
        
        # Check 1: last_week_target_total is present
        if last_week_target_total is None:
            print(f"    ❌ FAIL: last_week_target_total is missing")
            all_passed = False
            continue
        
        # Check 2: coll_pct calculation
        if last_week_target_total > 0:
            expected_coll_pct = round(collected * 100 / last_week_target_total, 2)
            if abs(coll_pct - expected_coll_pct) > 0.01:
                print(f"    ❌ FAIL: coll_pct {coll_pct} != expected {expected_coll_pct}")
                all_passed = False
            else:
                print(f"    ✓ coll_pct calculation correct: {coll_pct}%")
        else:
            if coll_pct != 0:
                print(f"    ❌ FAIL: coll_pct should be 0 when last_week_target_total is 0, got {coll_pct}")
                all_passed = False
            else:
                print(f"    ✓ coll_pct is 0 (last_week_target_total is 0)")
    
    return all_passed

def test_rep_history():
    """
    Test 3: GET /api/reps/Arun/history
    For each point:
    - Look up the corresponding meeting and find rep Arun
    - Let lwt = rep.last_week_target
    - If lwt > 0: assert point.coll_pct == round(point.collected * 100 / lwt, 2)
    - If lwt == 0: assert point.coll_pct == 0
    """
    print("\n=== TEST 3: GET /api/reps/Arun/history ===")
    
    # First get all meetings to build a lookup map
    resp = session.get(f"{BASE_URL}/meetings")
    if resp.status_code != 200:
        print(f"ERROR: Failed to get meetings for lookup - {resp.text}")
        return False
    
    meetings = resp.json()
    meeting_map = {}
    for m in meetings:
        meeting_date = m.get("meeting_date")
        for rep in m.get("reps", []):
            if rep.get("name", "").strip().lower() == "arun":
                meeting_map[meeting_date] = rep
                break
    
    print(f"Found {len(meeting_map)} meetings with rep 'Arun'")
    
    # Now get Arun's history
    resp = session.get(f"{BASE_URL}/reps/Arun/history")
    print(f"GET /api/reps/Arun/history: {resp.status_code}")
    
    if resp.status_code != 200:
        print(f"ERROR: Failed to get rep history - {resp.text}")
        return False
    
    data = resp.json()
    points = data.get("points", [])
    print(f"Found {len(points)} history points for Arun")
    
    all_passed = True
    for idx, point in enumerate(points):
        meeting_date = point.get("meeting_date", "unknown")
        print(f"\n  Point {idx+1}: {meeting_date}")
        
        coll_pct = point.get("coll_pct")
        collected = point.get("collected", 0)
        
        print(f"    collected: {collected}")
        print(f"    coll_pct: {coll_pct}")
        
        # Look up the rep data from the meeting
        rep = meeting_map.get(meeting_date)
        if not rep:
            print(f"    ⚠ WARNING: Could not find rep Arun in meeting {meeting_date}")
            continue
        
        lwt = rep.get("last_week_target", 0)
        print(f"    rep.last_week_target: {lwt}")
        
        # Check coll_pct calculation
        if lwt > 0:
            expected_coll_pct = round(collected * 100 / lwt, 2)
            if abs(coll_pct - expected_coll_pct) > 0.01:
                print(f"    ❌ FAIL: coll_pct {coll_pct} != expected {expected_coll_pct}")
                all_passed = False
            else:
                print(f"    ✓ coll_pct calculation correct: {coll_pct}%")
        else:
            if coll_pct != 0:
                print(f"    ❌ FAIL: coll_pct should be 0 when lwt is 0, got {coll_pct}")
                all_passed = False
            else:
                print(f"    ✓ coll_pct is 0 (lwt is 0)")
    
    return all_passed

def test_round_trip():
    """
    Test 4: Round-trip POST/DELETE
    - POST /api/meetings with unique meeting_date and two reps:
      - rep A: last_week_target=1000, weekly_collection={mbs:100, mcorp:150}
      - rep B: last_week_target=500, weekly_collection={mbs:50, mcorp:0}
    - GET the created meeting: assert summary.last_week_target_total == 1500
      and summary.coll_pct == round(300 * 100 / 1500, 2) == 20.0
    - DELETE the meeting and confirm GET returns 404
    """
    print("\n=== TEST 4: Round-trip POST/DELETE ===")
    
    # Create unique meeting date
    test_date = "2099-01-05"
    
    # Prepare test meeting data
    test_meeting = {
        "title": "Test Collection % Formula",
        "meeting_date": test_date,
        "period_start": test_date,
        "period_end": test_date,
        "notes": "Test meeting for collection % formula verification",
        "reps": [
            {
                "name": "Test Rep A",
                "aging": {
                    "d90": {"mbs": 100, "mcorp": 50},
                    "d60": {"mbs": 0, "mcorp": 0},
                    "d30": {"mbs": 0, "mcorp": 0},
                    "d15": {"mbs": 0, "mcorp": 0},
                    "othera": {"mbs": 0, "mcorp": 0}
                },
                "weekly_collection": {"mbs": 100, "mcorp": 150},
                "last_week_target": 1000,
                "working_days": 6
            },
            {
                "name": "Test Rep B",
                "aging": {
                    "d90": {"mbs": 50, "mcorp": 25},
                    "d60": {"mbs": 0, "mcorp": 0},
                    "d30": {"mbs": 0, "mcorp": 0},
                    "d15": {"mbs": 0, "mcorp": 0},
                    "othera": {"mbs": 0, "mcorp": 0}
                },
                "weekly_collection": {"mbs": 50, "mcorp": 0},
                "last_week_target": 500,
                "working_days": 6
            }
        ],
        "branches": [
            {
                "name": "Test Branch",
                "purchase": {"tons": {"mbs": 10, "mcorp": 5}, "value": {"mbs": 0, "mcorp": 0}},
                "sales": {"tons": {"mbs": 8, "mcorp": 4}, "value": {"mbs": 0, "mcorp": 0}},
                "sales_return": {"amount": {"mbs": 0, "mcorp": 0}, "count": {"mbs": 0, "mcorp": 0}}
            }
        ],
        "marketing_reps": [],
        "quotation": {
            "prepair": {"mbs": 0, "mcorp": 0},
            "conform": {"mbs": 0, "mcorp": 0},
            "pending": {"mbs": 0, "mcorp": 0},
            "under_process": {"mbs": 0, "mcorp": 0},
            "not_conform": {"mbs": 0, "mcorp": 0}
        },
        "financials": {
            "sales_value": {"mbs": 0, "mcorp": 0},
            "purchase_value": {"mbs": 0, "mcorp": 0}
        }
    }
    
    # POST the meeting
    print(f"\nCreating test meeting with date {test_date}...")
    resp = session.post(f"{BASE_URL}/meetings", json=test_meeting)
    print(f"POST /api/meetings: {resp.status_code}")
    
    if resp.status_code != 200:
        print(f"ERROR: Failed to create meeting - {resp.text}")
        return False
    
    created = resp.json()
    meeting_id = created.get("id")
    print(f"✓ Created meeting with ID: {meeting_id}")
    
    # Verify the calculations
    summary = created.get("summary", {})
    last_week_target_total = summary.get("last_week_target_total")
    coll_pct = summary.get("coll_pct")
    collected = summary.get("collected")
    
    print(f"\nVerifying calculations:")
    print(f"  summary.last_week_target_total: {last_week_target_total}")
    print(f"  summary.collected: {collected}")
    print(f"  summary.coll_pct: {coll_pct}")
    
    all_passed = True
    
    # Check 1: last_week_target_total == 1500
    if last_week_target_total != 1500:
        print(f"  ❌ FAIL: last_week_target_total {last_week_target_total} != expected 1500")
        all_passed = False
    else:
        print(f"  ✓ last_week_target_total is correct: 1500")
    
    # Check 2: collected == 300 (100+150+50+0)
    if collected != 300:
        print(f"  ❌ FAIL: collected {collected} != expected 300")
        all_passed = False
    else:
        print(f"  ✓ collected is correct: 300")
    
    # Check 3: coll_pct == 20.0 (300 * 100 / 1500)
    expected_coll_pct = 20.0
    if abs(coll_pct - expected_coll_pct) > 0.01:
        print(f"  ❌ FAIL: coll_pct {coll_pct} != expected {expected_coll_pct}")
        all_passed = False
    else:
        print(f"  ✓ coll_pct is correct: {coll_pct}%")
    
    # GET the meeting to verify it persisted correctly
    print(f"\nVerifying meeting persisted correctly...")
    resp = session.get(f"{BASE_URL}/meetings/{meeting_id}")
    print(f"GET /api/meetings/{meeting_id}: {resp.status_code}")
    
    if resp.status_code != 200:
        print(f"ERROR: Failed to get created meeting - {resp.text}")
        all_passed = False
    else:
        retrieved = resp.json()
        retrieved_summary = retrieved.get("summary", {})
        if retrieved_summary.get("last_week_target_total") == 1500 and \
           abs(retrieved_summary.get("coll_pct", 0) - 20.0) < 0.01:
            print(f"✓ Meeting persisted correctly with correct calculations")
        else:
            print(f"❌ FAIL: Retrieved meeting has incorrect calculations")
            all_passed = False
    
    # DELETE the meeting
    print(f"\nCleaning up: deleting test meeting...")
    resp = session.delete(f"{BASE_URL}/meetings/{meeting_id}")
    print(f"DELETE /api/meetings/{meeting_id}: {resp.status_code}")
    
    if resp.status_code != 200:
        print(f"ERROR: Failed to delete meeting - {resp.text}")
        all_passed = False
    else:
        print(f"✓ Meeting deleted successfully")
    
    # Verify DELETE worked (should get 404)
    print(f"\nVerifying meeting was deleted...")
    resp = session.get(f"{BASE_URL}/meetings/{meeting_id}")
    print(f"GET /api/meetings/{meeting_id}: {resp.status_code}")
    
    if resp.status_code != 404:
        print(f"❌ FAIL: Expected 404 after delete, got {resp.status_code}")
        all_passed = False
    else:
        print(f"✓ Confirmed meeting no longer exists (404)")
    
    return all_passed

def main():
    print("=" * 70)
    print("COLLECTION % FORMULA CHANGE - BACKEND TESTING")
    print("=" * 70)
    print(f"Backend URL: {BASE_URL}")
    print(f"Test Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Login
    login()
    
    # Run all tests
    results = {
        "Test 1: GET /api/meetings": test_meetings_endpoint(),
        "Test 2: GET /api/analytics/trends": test_trends_endpoint(),
        "Test 3: GET /api/reps/Arun/history": test_rep_history(),
        "Test 4: Round-trip POST/DELETE": test_round_trip()
    }
    
    # Summary
    print("\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)
    
    all_passed = True
    for test_name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status} - {test_name}")
        if not passed:
            all_passed = False
    
    print("=" * 70)
    
    if all_passed:
        print("\n🎉 ALL TESTS PASSED - Collection % formula change is working correctly!")
        return 0
    else:
        print("\n⚠️  SOME TESTS FAILED - See details above")
        return 1

if __name__ == "__main__":
    sys.exit(main())
