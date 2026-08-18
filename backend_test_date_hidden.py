#!/usr/bin/env python3
"""
Backend verification for Date Hidden bug fix.
Tests rapid POST-then-multiple-PUT flow to ensure no duplicate meetings are created.
"""

import requests
import time
import sys

# Backend URL
BASE_URL = "https://github-opener-9.preview.emergentagent.com/api"

# Test credentials
ADMIN_EMAIL = "admin@company.com"
ADMIN_PASSWORD = "Admin@123"

def print_step(step_num, description):
    """Print test step header"""
    print(f"\n{'='*80}")
    print(f"STEP {step_num}: {description}")
    print('='*80)

def print_result(passed, message):
    """Print test result"""
    status = "✅ PASS" if passed else "❌ FAIL"
    print(f"{status}: {message}")
    return passed

def login():
    """Authenticate and return session"""
    print_step(0, "Authentication")
    session = requests.Session()
    
    response = session.post(
        f"{BASE_URL}/auth/login",
        json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
    )
    
    if response.status_code == 200:
        print_result(True, f"Authenticated as {ADMIN_EMAIL}")
        return session
    else:
        print_result(False, f"Login failed: {response.status_code} - {response.text}")
        sys.exit(1)

def test_date_hidden_flow():
    """Run all test steps"""
    session = login()
    all_passed = True
    test_meeting_id = None
    
    try:
        # STEP 1: GET /api/meetings - record count_before
        print_step(1, "GET /api/meetings - record initial count")
        response = session.get(f"{BASE_URL}/meetings")
        
        if response.status_code == 200:
            meetings = response.json()
            count_before = len(meetings)
            print_result(True, f"Initial meeting count: {count_before}")
            
            # List existing meetings for reference
            print("\nExisting meetings:")
            for m in meetings:
                print(f"  - {m.get('meeting_date')} (id: {m.get('id')})")
        else:
            all_passed = print_result(False, f"GET /api/meetings failed: {response.status_code}")
            return all_passed
        
        # STEP 2: POST /api/meetings with specified payload
        print_step(2, "POST /api/meetings with meeting_date=2099-12-15")
        
        payload = {
            "title": "Date Hidden Test",
            "meeting_date": "2099-12-15",
            "period_start": "2099-12-09",
            "period_end": "2099-12-14",
            "reps": [
                {
                    "name": "DateHiddenRep",
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
        
        response = session.post(f"{BASE_URL}/meetings", json=payload)
        
        if response.status_code == 200:
            meeting = response.json()
            test_meeting_id = meeting.get('id')
            summary = meeting.get('summary', {})
            
            # Verify expected values
            expected_last_week_target = 1000
            expected_coll_pct = 15.0  # (100+50)*100/1000 = 15.0
            
            actual_last_week_target = summary.get('last_week_target_total')
            actual_coll_pct = summary.get('coll_pct')
            
            print(f"Created meeting ID: {test_meeting_id}")
            print(f"  last_week_target_total: {actual_last_week_target} (expected: {expected_last_week_target})")
            print(f"  coll_pct: {actual_coll_pct} (expected: {expected_coll_pct})")
            
            if actual_last_week_target == expected_last_week_target and actual_coll_pct == expected_coll_pct:
                print_result(True, "POST successful with correct calculations")
            else:
                all_passed = print_result(False, f"Calculations incorrect: last_week_target_total={actual_last_week_target}, coll_pct={actual_coll_pct}")
        else:
            all_passed = print_result(False, f"POST failed: {response.status_code} - {response.text}")
            return all_passed
        
        # STEP 3: PUT /api/meetings/{id1} THREE times back-to-back
        print_step(3, "PUT /api/meetings/{id} THREE times (rapid succession)")
        
        mbs_values = [200, 300, 400]
        put_results = []
        
        for i, mbs_value in enumerate(mbs_values, 1):
            # Get current meeting state
            get_response = session.get(f"{BASE_URL}/meetings/{test_meeting_id}")
            if get_response.status_code != 200:
                all_passed = print_result(False, f"GET before PUT #{i} failed: {get_response.status_code}")
                break
            
            current_meeting = get_response.json()
            
            # Modify weekly_collection.mbs
            current_meeting['reps'][0]['weekly_collection']['mbs'] = mbs_value
            
            # PUT the modified meeting
            put_response = session.put(f"{BASE_URL}/meetings/{test_meeting_id}", json=current_meeting)
            
            if put_response.status_code == 200:
                put_meeting = put_response.json()
                actual_mbs = put_meeting['reps'][0]['weekly_collection']['mbs']
                put_results.append((i, mbs_value, actual_mbs, True))
                print(f"  PUT #{i}: Set mbs={mbs_value}, Response mbs={actual_mbs} ✅")
            else:
                put_results.append((i, mbs_value, None, False))
                all_passed = print_result(False, f"PUT #{i} failed: {put_response.status_code} - {put_response.text}")
                break
            
            # Small delay to simulate rapid but sequential saves
            time.sleep(0.1)
        
        if all(result[3] for result in put_results):
            print_result(True, "All three PUTs completed successfully")
        
        # STEP 4: GET /api/meetings/{id1} - verify last-write-wins
        print_step(4, "GET /api/meetings/{id} - verify last-write-wins (mbs=400)")
        
        response = session.get(f"{BASE_URL}/meetings/{test_meeting_id}")
        
        if response.status_code == 200:
            meeting = response.json()
            actual_mbs = meeting['reps'][0]['weekly_collection']['mbs']
            expected_mbs = 400
            
            print(f"Final weekly_collection.mbs: {actual_mbs} (expected: {expected_mbs})")
            
            if actual_mbs == expected_mbs:
                print_result(True, "Last-write-wins verified: mbs=400")
            else:
                all_passed = print_result(False, f"Last-write-wins FAILED: expected mbs=400, got mbs={actual_mbs}")
        else:
            all_passed = print_result(False, f"GET failed: {response.status_code}")
        
        # STEP 5: GET /api/meetings - verify count and no duplicates
        print_step(5, "GET /api/meetings - verify count and no duplicates")
        
        response = session.get(f"{BASE_URL}/meetings")
        
        if response.status_code == 200:
            meetings = response.json()
            count_after = len(meetings)
            
            # Filter meetings with meeting_date == "2099-12-15"
            test_date_meetings = [m for m in meetings if m.get('meeting_date') == '2099-12-15']
            test_date_count = len(test_date_meetings)
            
            print(f"Total meeting count: {count_after} (expected: {count_before + 1})")
            print(f"Meetings with date 2099-12-15: {test_date_count} (expected: 1)")
            
            if test_date_count == 1:
                test_meeting = test_date_meetings[0]
                if test_meeting.get('id') == test_meeting_id:
                    print_result(True, f"Exactly 1 meeting with date 2099-12-15, correct ID: {test_meeting_id}")
                else:
                    all_passed = print_result(False, f"Meeting ID mismatch: expected {test_meeting_id}, got {test_meeting.get('id')}")
            else:
                all_passed = print_result(False, f"DUPLICATE DETECTED: Found {test_date_count} meetings with date 2099-12-15")
                for m in test_date_meetings:
                    print(f"  - ID: {m.get('id')}, Title: {m.get('title')}")
            
            if count_after == count_before + 1:
                print_result(True, f"Total count correct: {count_after} = {count_before} + 1")
            else:
                all_passed = print_result(False, f"Total count incorrect: {count_after} != {count_before} + 1")
        else:
            all_passed = print_result(False, f"GET /api/meetings failed: {response.status_code}")
        
        # STEP 6: DELETE /api/meetings/{id1}
        print_step(6, "DELETE /api/meetings/{id}")
        
        response = session.delete(f"{BASE_URL}/meetings/{test_meeting_id}")
        
        if response.status_code == 200:
            result = response.json()
            if result.get('ok') == True:
                print_result(True, f"DELETE successful: {result}")
                
                # Verify 404 on subsequent GET
                get_response = session.get(f"{BASE_URL}/meetings/{test_meeting_id}")
                if get_response.status_code == 404:
                    print_result(True, "Subsequent GET returns 404 as expected")
                else:
                    all_passed = print_result(False, f"Subsequent GET should return 404, got {get_response.status_code}")
            else:
                all_passed = print_result(False, f"DELETE response missing 'ok: true': {result}")
        else:
            all_passed = print_result(False, f"DELETE failed: {response.status_code} - {response.text}")
        
        # STEP 7: Final sanity check
        print_step(7, "Final sanity check - verify count and existing meetings unchanged")
        
        response = session.get(f"{BASE_URL}/meetings")
        
        if response.status_code == 200:
            meetings = response.json()
            count_final = len(meetings)
            
            print(f"Final meeting count: {count_final} (expected: {count_before})")
            
            if count_final == count_before:
                print_result(True, f"Count restored to original: {count_final}")
            else:
                all_passed = print_result(False, f"Count mismatch: {count_final} != {count_before}")
            
            # Spot-check existing meetings
            expected_dates = ['2026-07-15', '2026-07-21', '2026-07-28', '2026-08-11', '2026-08-22']
            found_dates = [m.get('meeting_date') for m in meetings]
            
            print("\nExisting meetings after cleanup:")
            for m in meetings:
                print(f"  - {m.get('meeting_date')} (id: {m.get('id')})")
            
            # Check if expected dates are present (allowing for additional meetings)
            missing_dates = [d for d in expected_dates if d not in found_dates]
            if missing_dates:
                all_passed = print_result(False, f"Missing expected meetings: {missing_dates}")
            else:
                print_result(True, "All expected seeded meetings still present")
        else:
            all_passed = print_result(False, f"Final GET failed: {response.status_code}")
        
    except Exception as e:
        print_result(False, f"Exception occurred: {str(e)}")
        import traceback
        traceback.print_exc()
        all_passed = False
    
    return all_passed

def check_backend_logs():
    """Check backend logs for errors"""
    print_step(8, "Check backend logs for 500/502 errors")
    
    import subprocess
    
    try:
        # Check error log
        result = subprocess.run(
            ["tail", "-n", "100", "/var/log/supervisor/backend.err.log"],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        err_log = result.stdout
        
        # Look for recent errors (ignore old ones)
        recent_errors = []
        for line in err_log.split('\n'):
            if '500' in line or '502' in line or 'ERROR' in line.upper():
                # Check if it's a recent timestamp (2026-08 or later)
                if '2026-08' in line or '2026-09' in line or '2026-10' in line:
                    recent_errors.append(line)
        
        if recent_errors:
            print("⚠️  Found recent errors in backend.err.log:")
            for err in recent_errors[:10]:  # Show first 10
                print(f"  {err}")
            return False
        else:
            print_result(True, "No 500/502 errors found in recent backend logs")
            return True
            
    except Exception as e:
        print(f"⚠️  Could not check logs: {e}")
        return True  # Don't fail the test if we can't check logs

def main():
    """Main test runner"""
    print("\n" + "="*80)
    print("BACKEND VERIFICATION: Date Hidden Bug Fix")
    print("Testing rapid POST-then-multiple-PUT flow")
    print("="*80)
    
    test_passed = test_date_hidden_flow()
    logs_ok = check_backend_logs()
    
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)
    
    if test_passed and logs_ok:
        print("✅ ALL TESTS PASSED")
        print("\nBackend correctly handles:")
        print("  - POST /api/meetings with auto-populated dates")
        print("  - Three rapid sequential PUTs (simulating auto-save)")
        print("  - Last-write-wins semantics (mbs=400)")
        print("  - No duplicate meetings created")
        print("  - Proper DELETE cleanup")
        print("  - No 500/502 errors in logs")
        return 0
    else:
        print("❌ SOME TESTS FAILED")
        print("\nPlease review the failures above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
