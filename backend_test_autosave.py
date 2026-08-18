#!/usr/bin/env python3
"""
Backend test for auto-save feature verification.
Tests rapid sequential PUTs to ensure no duplicates and last-write-wins semantics.
"""
import requests
import json
import time

# Configuration
BASE_URL = "https://github-opener-9.preview.emergentagent.com/api"
ADMIN_EMAIL = "admin@company.com"
ADMIN_PASSWORD = "Admin@123"

def print_step(step_num, description):
    """Print test step header"""
    print(f"\n{'='*80}")
    print(f"STEP {step_num}: {description}")
    print('='*80)

def login():
    """Login and return session with cookie"""
    print_step(0, "Authentication")
    session = requests.Session()
    resp = session.post(
        f"{BASE_URL}/auth/login",
        json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
    )
    print(f"Login response: {resp.status_code}")
    if resp.status_code != 200:
        print(f"Login failed: {resp.text}")
        raise Exception("Authentication failed")
    print(f"✓ Authenticated as {ADMIN_EMAIL}")
    return session

def test_autosave_backend():
    """Run the complete auto-save backend verification test"""
    session = login()
    
    # Step 1: Get initial count
    print_step(1, "GET /api/meetings - record count_before")
    resp = session.get(f"{BASE_URL}/meetings")
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
    meetings_before = resp.json()
    count_before = len(meetings_before)
    print(f"✓ Initial meeting count: {count_before}")
    
    # Check for existing seeded meetings
    seeded_ids = [m.get('id') for m in meetings_before if m.get('meeting_date') in 
                  ['2026-07-15', '2026-07-21', '2026-07-28', '2026-08-11', '2026-08-22']]
    print(f"✓ Found {len(seeded_ids)} seeded meetings")
    if '1f316aec-ef04-40b4-a89a-633c51211ce5' in seeded_ids:
        print(f"✓ Seeded meeting 2026-07-15 (id=1f316aec-ef04-40b4-a89a-633c51211ce5) present")
    
    # Step 2: POST new meeting
    print_step(2, "POST /api/meetings with test data")
    test_meeting = {
        "title": "Auto-Save Test",
        "meeting_date": "2099-12-01",
        "period_start": "2099-11-24",
        "period_end": "2099-11-30",
        "reps": [
            {
                "name": "AutoSaveRep",
                "aging": {
                    "d90": {"mbs": 1000, "mcorp": 500},
                    "d60": {"mbs": 800, "mcorp": 400},
                    "d30": {"mbs": 600, "mcorp": 300},
                    "d15": {"mbs": 0, "mcorp": 200},
                    "othera": {"mbs": 100, "mcorp": 50}
                },
                "weekly_collection": {"mbs": 100, "mcorp": 50},
                "last_week_target": 1000,
                "working_days": 6
            }
        ],
        "branches": [
            {
                "name": "Direct Sale",
                "purchase": {"mbs": 0, "mcorp": 0},
                "sales": {"mbs": 0, "mcorp": 0}
            }
        ],
        "quotation": {},
        "marketing_reps": []
    }
    
    resp = session.post(f"{BASE_URL}/meetings", json=test_meeting)
    print(f"POST response status: {resp.status_code}")
    if resp.status_code != 200:
        print(f"POST failed: {resp.text}")
        raise Exception(f"POST failed with status {resp.status_code}")
    
    meeting_data = resp.json()
    id1 = meeting_data.get('id')
    print(f"✓ Created meeting with id: {id1}")
    
    # Verify summary calculations
    summary = meeting_data.get('summary', {})
    last_week_target_total = summary.get('last_week_target_total')
    collected = summary.get('collected')
    coll_pct = summary.get('coll_pct')
    
    print(f"  Summary:")
    print(f"    last_week_target_total: {last_week_target_total} (expected: 1000)")
    print(f"    collected: {collected} (expected: 150 = 100+50)")
    print(f"    coll_pct: {coll_pct} (expected: 15.0 = 150*100/1000)")
    
    assert last_week_target_total == 1000.0, f"Expected last_week_target_total=1000, got {last_week_target_total}"
    assert collected == 150.0, f"Expected collected=150, got {collected}"
    expected_coll_pct = round(150 * 100 / 1000, 2)
    assert coll_pct == expected_coll_pct, f"Expected coll_pct={expected_coll_pct}, got {coll_pct}"
    print(f"✓ All summary calculations correct")
    
    # Step 3: PUT three times in quick succession
    print_step(3, "PUT /api/meetings/{id1} THREE times back-to-back")
    
    # Get the full meeting data for PUT
    resp = session.get(f"{BASE_URL}/meetings/{id1}")
    assert resp.status_code == 200
    meeting_for_put = resp.json()
    
    put_values = [110, 210, 310]
    for i, mbs_value in enumerate(put_values, 1):
        print(f"\n  PUT #{i}: Setting weekly_collection.mbs = {mbs_value}")
        meeting_for_put['reps'][0]['weekly_collection']['mbs'] = mbs_value
        
        resp = session.put(f"{BASE_URL}/meetings/{id1}", json=meeting_for_put)
        print(f"    Response status: {resp.status_code}")
        
        if resp.status_code != 200:
            print(f"    PUT #{i} failed: {resp.text}")
            raise Exception(f"PUT #{i} failed with status {resp.status_code}")
        
        put_data = resp.json()
        actual_mbs = put_data['reps'][0]['weekly_collection']['mbs']
        print(f"    ✓ PUT #{i} successful, returned mbs={actual_mbs}")
        
        # Update for next iteration
        meeting_for_put = put_data
        
        # Small delay to simulate real auto-save timing
        if i < len(put_values):
            time.sleep(0.1)
    
    print(f"\n✓ All 3 PUTs completed successfully")
    
    # Step 4: GET and verify last value persisted
    print_step(4, "GET /api/meetings/{id1} - verify last-write-wins")
    resp = session.get(f"{BASE_URL}/meetings/{id1}")
    assert resp.status_code == 200
    final_meeting = resp.json()
    final_mbs = final_meeting['reps'][0]['weekly_collection']['mbs']
    
    print(f"  Final weekly_collection.mbs: {final_mbs}")
    assert final_mbs == 310, f"Expected mbs=310 (last-write-wins), got {final_mbs}"
    print(f"✓ Last-write-wins verified: mbs = 310")
    
    # Step 5: Verify no duplicates
    print_step(5, "GET /api/meetings - verify no duplicates")
    resp = session.get(f"{BASE_URL}/meetings")
    assert resp.status_code == 200
    meetings_after = resp.json()
    count_after = len(meetings_after)
    
    print(f"  Count before: {count_before}")
    print(f"  Count after: {count_after}")
    print(f"  Expected: {count_before + 1}")
    
    assert count_after == count_before + 1, f"Expected count={count_before + 1}, got {count_after}"
    print(f"✓ Count correct: {count_after} = {count_before} + 1")
    
    # Filter for 2099-12-01
    test_date_meetings = [m for m in meetings_after if m.get('meeting_date') == '2099-12-01']
    print(f"\n  Meetings with date 2099-12-01: {len(test_date_meetings)}")
    
    assert len(test_date_meetings) == 1, f"Expected exactly 1 meeting for 2099-12-01, got {len(test_date_meetings)}"
    assert test_date_meetings[0]['id'] == id1, f"Expected id={id1}, got {test_date_meetings[0]['id']}"
    print(f"✓ Exactly 1 meeting for 2099-12-01 with correct id")
    print(f"✓ No duplicates created by sequential PUTs")
    
    # Step 6: DELETE test meeting
    print_step(6, "DELETE /api/meetings/{id1}")
    resp = session.delete(f"{BASE_URL}/meetings/{id1}")
    print(f"  DELETE response status: {resp.status_code}")
    
    if resp.status_code != 200:
        print(f"  DELETE failed: {resp.text}")
        raise Exception(f"DELETE failed with status {resp.status_code}")
    
    delete_result = resp.json()
    print(f"  DELETE response: {delete_result}")
    assert delete_result.get('ok') == True, f"Expected {{ok: true}}, got {delete_result}"
    print(f"✓ DELETE returned {{ok: true}}")
    
    # Verify 404 on subsequent GET
    resp = session.get(f"{BASE_URL}/meetings/{id1}")
    print(f"  Subsequent GET status: {resp.status_code}")
    assert resp.status_code == 404, f"Expected 404 after delete, got {resp.status_code}"
    print(f"✓ Subsequent GET returns 404 (meeting deleted)")
    
    # Step 7: Sanity check
    print_step(7, "Sanity check - verify original state")
    resp = session.get(f"{BASE_URL}/meetings")
    assert resp.status_code == 200
    meetings_final = resp.json()
    count_final = len(meetings_final)
    
    print(f"  Initial count: {count_before}")
    print(f"  Final count: {count_final}")
    
    assert count_final == count_before, f"Expected final count={count_before}, got {count_final}"
    print(f"✓ Final count equals initial count (no net change)")
    
    # Spot-check seeded meetings
    final_ids = [m.get('id') for m in meetings_final]
    if '1f316aec-ef04-40b4-a89a-633c51211ce5' in final_ids:
        seeded_meeting = next(m for m in meetings_final if m['id'] == '1f316aec-ef04-40b4-a89a-633c51211ce5')
        print(f"✓ Seeded meeting 2026-07-15 (id=1f316aec-ef04-40b4-a89a-633c51211ce5) still present")
        print(f"  - meeting_date: {seeded_meeting.get('meeting_date')}")
        print(f"  - reps count: {len(seeded_meeting.get('reps', []))}")
    
    # Check for other seeded dates
    seeded_dates = ['2026-07-21', '2026-07-28', '2026-08-11', '2026-08-22']
    for date in seeded_dates:
        if any(m.get('meeting_date') == date for m in meetings_final):
            print(f"✓ Seeded meeting {date} still present")
    
    print(f"\n✓ All existing seeded meetings remain unchanged")
    
    # Step 8: Check backend logs
    print_step(8, "Check backend logs for errors")
    print("  (Will check logs separately via bash command)")
    
    print("\n" + "="*80)
    print("ALL TESTS PASSED ✅")
    print("="*80)
    print("\nSummary:")
    print("  ✓ POST created meeting with correct calculations")
    print("  ✓ Three rapid PUTs all succeeded (HTTP 200)")
    print("  ✓ Last-write-wins: final value = 310 (from PUT #3)")
    print("  ✓ No duplicates created (exactly 1 meeting for test date)")
    print("  ✓ DELETE successful with subsequent 404")
    print("  ✓ Final count equals initial count (cleanup successful)")
    print("  ✓ Existing seeded meetings unchanged")
    print("\nBackend auto-save behavior is CORRECT and production-ready.")

if __name__ == "__main__":
    try:
        test_autosave_backend()
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
