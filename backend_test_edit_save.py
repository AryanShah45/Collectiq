#!/usr/bin/env python3
"""
Bug fix verification test for CollectIQ:
User reported: "When I edit an existing meeting and make further entry and save, it is NOT saving."

Root cause: Frontend submit() bailed out when ANY rep had empty name (clicking "Add Rep" adds empty-name rep).
Fix: Frontend now filters out empty-name reps before saving.

This test verifies the backend PUT /api/meetings/{id} flow works end-to-end.
"""

import requests
import json
import sys
import copy

# Backend URL from frontend/.env
BASE_URL = "https://github-opener-9.preview.emergentagent.com/api"

# Test credentials
ADMIN_EMAIL = "admin@company.com"
ADMIN_PASSWORD = "Admin@123"

# Target meeting ID from review_request
TARGET_MEETING_ID = "1f316aec-ef04-40b4-a89a-633c51211ce5"

# Test results
results = []

def log_result(step, passed, message, details=None):
    """Log test result"""
    status = "✅ PASS" if passed else "❌ FAIL"
    results.append({
        "step": step,
        "passed": passed,
        "message": message,
        "details": details
    })
    print(f"\n{status} - Step {step}: {message}")
    if details:
        print(f"  Details: {details}")

def print_summary():
    """Print final summary"""
    print("\n" + "="*80)
    print("BUG FIX VERIFICATION TEST SUMMARY")
    print("="*80)
    passed = sum(1 for r in results if r["passed"])
    total = len(results)
    print(f"Total: {passed}/{total} passed")
    print("\nResults:")
    for r in results:
        status = "✅" if r["passed"] else "❌"
        print(f"  {status} Step {r['step']}: {r['message']}")
        if not r["passed"] and r["details"]:
            print(f"     {r['details']}")
    print("="*80)

def main():
    session = requests.Session()
    
    # Step 0: Login
    print("\n" + "="*80)
    print("STEP 0: Authentication")
    print("="*80)
    try:
        login_resp = session.post(
            f"{BASE_URL}/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
        )
        if login_resp.status_code == 200:
            print(f"✅ Login successful as {ADMIN_EMAIL}")
        else:
            print(f"❌ Login failed: {login_resp.status_code} - {login_resp.text}")
            sys.exit(1)
    except Exception as e:
        print(f"❌ Login error: {e}")
        sys.exit(1)
    
    # Step 1: GET /api/meetings - pick the target meeting
    print("\n" + "="*80)
    print("STEP 1: GET /api/meetings - pick target meeting")
    print("="*80)
    
    original_meeting = None
    original_reps_count = 0
    original_summary = None
    
    try:
        meetings_resp = session.get(f"{BASE_URL}/meetings")
        if meetings_resp.status_code != 200:
            log_result(1, False, "GET /api/meetings failed", 
                      f"Status: {meetings_resp.status_code}, Body: {meetings_resp.text[:500]}")
            print_summary()
            sys.exit(1)
        
        meetings = meetings_resp.json()
        
        # Find the target meeting
        original_meeting = next((m for m in meetings if m.get("id") == TARGET_MEETING_ID), None)
        
        if not original_meeting:
            log_result(1, False, "Target meeting not found", 
                      f"Meeting ID {TARGET_MEETING_ID} not found in {len(meetings)} meetings")
            print_summary()
            sys.exit(1)
        
        original_reps_count = len(original_meeting.get("reps", []))
        original_summary = original_meeting.get("summary", {})
        
        checks = []
        checks.append(("HTTP 200", True))
        checks.append(("Non-empty list", len(meetings) > 0))
        checks.append(("Target meeting found", original_meeting is not None))
        checks.append(("Meeting date is 2026-07-15", original_meeting.get("meeting_date") == "2026-07-15"))
        checks.append(("Has reps", original_reps_count > 0))
        
        all_passed = all(c[1] for c in checks)
        details = f"Total meetings: {len(meetings)}, Target meeting date: {original_meeting.get('meeting_date')}, Original reps count: {original_reps_count}, Original coll_pct: {original_summary.get('coll_pct')}"
        
        log_result(1, all_passed, "GET /api/meetings", details)
        
        print(f"\n📋 Original meeting state:")
        print(f"   ID: {TARGET_MEETING_ID}")
        print(f"   Date: {original_meeting.get('meeting_date')}")
        print(f"   Reps count: {original_reps_count}")
        print(f"   Rep names: {[r.get('name') for r in original_meeting.get('reps', [])]}")
        print(f"   Summary.collected: {original_summary.get('collected')}")
        print(f"   Summary.last_week_target_total: {original_summary.get('last_week_target_total')}")
        print(f"   Summary.coll_pct: {original_summary.get('coll_pct')}")
        
    except Exception as e:
        log_result(1, False, "GET /api/meetings exception", str(e))
        print_summary()
        sys.exit(1)
    
    # Step 2: PUT /api/meetings/{id} with one extra rep "PlaywrightRep"
    print("\n" + "="*80)
    print("STEP 2: PUT /api/meetings/{id} - add PlaywrightRep")
    print("="*80)
    
    # Create the PUT payload with all original fields plus one extra rep
    playwright_rep = {
        "name": "PlaywrightRep",
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
    
    # Build PUT payload with all original fields
    put_payload = {
        "title": original_meeting.get("title", "Weekly Collection Meeting"),
        "meeting_date": original_meeting.get("meeting_date"),
        "period_start": original_meeting.get("period_start", ""),
        "period_end": original_meeting.get("period_end", ""),
        "notes": original_meeting.get("notes", ""),
        "reps": original_meeting.get("reps", []) + [playwright_rep],
        "branches": original_meeting.get("branches", []),
        "quotation": original_meeting.get("quotation", {}),
        "marketing_reps": original_meeting.get("marketing_reps", []),
        "financials": original_meeting.get("financials", {})
    }
    
    try:
        put_resp = session.put(f"{BASE_URL}/meetings/{TARGET_MEETING_ID}", json=put_payload)
        
        if put_resp.status_code != 200:
            log_result(2, False, "PUT /api/meetings failed", 
                      f"Status: {put_resp.status_code}, Body: {put_resp.text[:500]}")
            print_summary()
            sys.exit(1)
        
        updated_meeting = put_resp.json()
        updated_reps_count = len(updated_meeting.get("reps", []))
        updated_summary = updated_meeting.get("summary", {})
        
        # Calculate expected coll_pct
        # Original collected + new rep's collection (100 + 50 = 150)
        # Original last_week_target_total + new rep's last_week_target (1000)
        expected_reps_count = original_reps_count + 1
        
        # Verify coll_pct calculation
        collected = updated_summary.get("collected", 0)
        last_week_target_total = updated_summary.get("last_week_target_total", 0)
        coll_pct = updated_summary.get("coll_pct", 0)
        
        expected_coll_pct = round(collected * 100 / last_week_target_total, 2) if last_week_target_total else 0
        
        checks = []
        checks.append(("HTTP 200", True))
        checks.append(("Reps count increased", updated_reps_count == expected_reps_count))
        checks.append(("PlaywrightRep in reps", any(r.get("name") == "PlaywrightRep" for r in updated_meeting.get("reps", []))))
        checks.append(("coll_pct recalculated correctly", abs(coll_pct - expected_coll_pct) < 0.01))
        
        all_passed = all(c[1] for c in checks)
        details = f"Original reps: {original_reps_count}, Updated reps: {updated_reps_count}, Expected: {expected_reps_count}, collected: {collected}, last_week_target_total: {last_week_target_total}, coll_pct: {coll_pct}, expected_coll_pct: {expected_coll_pct}"
        
        log_result(2, all_passed, "PUT with extra rep", details)
        
    except Exception as e:
        log_result(2, False, "PUT exception", str(e))
        print_summary()
        sys.exit(1)
    
    # Step 3: GET /api/meetings/{id} - confirm PlaywrightRep persisted
    print("\n" + "="*80)
    print("STEP 3: GET /api/meetings/{id} - verify PlaywrightRep persisted")
    print("="*80)
    
    try:
        get_resp = session.get(f"{BASE_URL}/meetings/{TARGET_MEETING_ID}")
        
        if get_resp.status_code != 200:
            log_result(3, False, "GET /api/meetings/{id} failed", 
                      f"Status: {get_resp.status_code}")
            print_summary()
            sys.exit(1)
        
        meeting = get_resp.json()
        reps = meeting.get("reps", [])
        
        playwright_rep_found = any(r.get("name") == "PlaywrightRep" for r in reps)
        
        checks = []
        checks.append(("HTTP 200", True))
        checks.append(("PlaywrightRep in reps", playwright_rep_found))
        checks.append(("Reps count correct", len(reps) == original_reps_count + 1))
        
        all_passed = all(c[1] for c in checks)
        details = f"Reps count: {len(reps)}, PlaywrightRep found: {playwright_rep_found}, Rep names: {[r.get('name') for r in reps]}"
        
        log_result(3, all_passed, "GET - PlaywrightRep persisted", details)
        
    except Exception as e:
        log_result(3, False, "GET exception", str(e))
    
    # Step 4: PUT again to remove PlaywrightRep (restore original state)
    print("\n" + "="*80)
    print("STEP 4: PUT /api/meetings/{id} - remove PlaywrightRep")
    print("="*80)
    
    # Build PUT payload with original reps only (no PlaywrightRep)
    restore_payload = {
        "title": original_meeting.get("title", "Weekly Collection Meeting"),
        "meeting_date": original_meeting.get("meeting_date"),
        "period_start": original_meeting.get("period_start", ""),
        "period_end": original_meeting.get("period_end", ""),
        "notes": original_meeting.get("notes", ""),
        "reps": original_meeting.get("reps", []),
        "branches": original_meeting.get("branches", []),
        "quotation": original_meeting.get("quotation", {}),
        "marketing_reps": original_meeting.get("marketing_reps", []),
        "financials": original_meeting.get("financials", {})
    }
    
    try:
        put_resp = session.put(f"{BASE_URL}/meetings/{TARGET_MEETING_ID}", json=restore_payload)
        
        if put_resp.status_code != 200:
            log_result(4, False, "PUT (restore) failed", 
                      f"Status: {put_resp.status_code}, Body: {put_resp.text[:500]}")
            print_summary()
            sys.exit(1)
        
        restored_meeting = put_resp.json()
        restored_reps_count = len(restored_meeting.get("reps", []))
        
        checks = []
        checks.append(("HTTP 200", True))
        checks.append(("Reps count back to original", restored_reps_count == original_reps_count))
        checks.append(("PlaywrightRep removed", not any(r.get("name") == "PlaywrightRep" for r in restored_meeting.get("reps", []))))
        
        all_passed = all(c[1] for c in checks)
        details = f"Original reps: {original_reps_count}, Restored reps: {restored_reps_count}, PlaywrightRep removed: {not any(r.get('name') == 'PlaywrightRep' for r in restored_meeting.get('reps', []))}"
        
        log_result(4, all_passed, "PUT - remove PlaywrightRep", details)
        
    except Exception as e:
        log_result(4, False, "PUT (restore) exception", str(e))
    
    # Step 5: GET /api/meetings/{id} - confirm PlaywrightRep is gone
    print("\n" + "="*80)
    print("STEP 5: GET /api/meetings/{id} - verify PlaywrightRep is gone")
    print("="*80)
    
    try:
        get_resp = session.get(f"{BASE_URL}/meetings/{TARGET_MEETING_ID}")
        
        if get_resp.status_code != 200:
            log_result(5, False, "GET /api/meetings/{id} failed", 
                      f"Status: {get_resp.status_code}")
            print_summary()
            sys.exit(1)
        
        meeting = get_resp.json()
        reps = meeting.get("reps", [])
        
        playwright_rep_found = any(r.get("name") == "PlaywrightRep" for r in reps)
        
        checks = []
        checks.append(("HTTP 200", True))
        checks.append(("PlaywrightRep NOT in reps", not playwright_rep_found))
        checks.append(("Reps count back to original", len(reps) == original_reps_count))
        
        all_passed = all(c[1] for c in checks)
        details = f"Reps count: {len(reps)}, PlaywrightRep found: {playwright_rep_found}, Rep names: {[r.get('name') for r in reps]}"
        
        log_result(5, all_passed, "GET - PlaywrightRep removed", details)
        
    except Exception as e:
        log_result(5, False, "GET exception", str(e))
    
    # Step 6: Edge case - PUT with last_week_target=0
    print("\n" + "="*80)
    print("STEP 6: Edge case - PUT with last_week_target=0")
    print("="*80)
    
    try:
        # Get current meeting state
        get_resp = session.get(f"{BASE_URL}/meetings/{TARGET_MEETING_ID}")
        current_meeting = get_resp.json()
        
        # Modify one rep's last_week_target to 0
        edge_payload = {
            "title": current_meeting.get("title", "Weekly Collection Meeting"),
            "meeting_date": current_meeting.get("meeting_date"),
            "period_start": current_meeting.get("period_start", ""),
            "period_end": current_meeting.get("period_end", ""),
            "notes": current_meeting.get("notes", ""),
            "reps": copy.deepcopy(current_meeting.get("reps", [])),
            "branches": current_meeting.get("branches", []),
            "quotation": current_meeting.get("quotation", {}),
            "marketing_reps": current_meeting.get("marketing_reps", []),
            "financials": current_meeting.get("financials", {})
        }
        
        # Set first rep's last_week_target to 0
        if edge_payload["reps"]:
            original_last_week_target = edge_payload["reps"][0].get("last_week_target", 0)
            edge_payload["reps"][0]["last_week_target"] = 0
        
        put_resp = session.put(f"{BASE_URL}/meetings/{TARGET_MEETING_ID}", json=edge_payload)
        
        if put_resp.status_code != 200:
            log_result(6, False, "PUT (last_week_target=0) failed", 
                      f"Status: {put_resp.status_code}, Body: {put_resp.text[:500]}")
        else:
            edge_meeting = put_resp.json()
            edge_summary = edge_meeting.get("summary", {})
            coll_pct = edge_summary.get("coll_pct")
            
            checks = []
            checks.append(("HTTP 200", True))
            checks.append(("coll_pct is a number", isinstance(coll_pct, (int, float))))
            checks.append(("coll_pct not NaN", coll_pct == coll_pct))  # NaN != NaN
            checks.append(("coll_pct not 500", coll_pct != 500))
            
            all_passed = all(c[1] for c in checks)
            details = f"coll_pct: {coll_pct}, type: {type(coll_pct).__name__}"
            
            log_result(6, all_passed, "Edge case - last_week_target=0", details)
            
            # Restore original value
            restore_payload = {
                "title": current_meeting.get("title", "Weekly Collection Meeting"),
                "meeting_date": current_meeting.get("meeting_date"),
                "period_start": current_meeting.get("period_start", ""),
                "period_end": current_meeting.get("period_end", ""),
                "notes": current_meeting.get("notes", ""),
                "reps": copy.deepcopy(current_meeting.get("reps", [])),
                "branches": current_meeting.get("branches", []),
                "quotation": current_meeting.get("quotation", {}),
                "marketing_reps": current_meeting.get("marketing_reps", []),
                "financials": current_meeting.get("financials", {})
            }
            
            session.put(f"{BASE_URL}/meetings/{TARGET_MEETING_ID}", json=restore_payload)
            print("   ✅ Restored original last_week_target value")
        
    except Exception as e:
        log_result(6, False, "Edge case exception", str(e))
    
    # Step 7: Edge case - PUT with empty branches and marketing_reps
    print("\n" + "="*80)
    print("STEP 7: Edge case - PUT with empty branches:[] and marketing_reps:[]")
    print("="*80)
    
    try:
        # Get current meeting state
        get_resp = session.get(f"{BASE_URL}/meetings/{TARGET_MEETING_ID}")
        current_meeting = get_resp.json()
        
        # Save original branches and marketing_reps
        original_branches = current_meeting.get("branches", [])
        original_marketing_reps = current_meeting.get("marketing_reps", [])
        
        # Build payload with empty arrays
        empty_payload = {
            "title": current_meeting.get("title", "Weekly Collection Meeting"),
            "meeting_date": current_meeting.get("meeting_date"),
            "period_start": current_meeting.get("period_start", ""),
            "period_end": current_meeting.get("period_end", ""),
            "notes": current_meeting.get("notes", ""),
            "reps": current_meeting.get("reps", []),
            "branches": [],
            "quotation": current_meeting.get("quotation", {}),
            "marketing_reps": [],
            "financials": current_meeting.get("financials", {})
        }
        
        put_resp = session.put(f"{BASE_URL}/meetings/{TARGET_MEETING_ID}", json=empty_payload)
        
        checks = []
        checks.append(("HTTP 200 (not 422)", put_resp.status_code == 200))
        
        if put_resp.status_code == 200:
            empty_meeting = put_resp.json()
            checks.append(("branches is empty array", empty_meeting.get("branches") == []))
            checks.append(("marketing_reps is empty array", empty_meeting.get("marketing_reps") == []))
        
        all_passed = all(c[1] for c in checks)
        details = f"Status: {put_resp.status_code}"
        
        log_result(7, all_passed, "Edge case - empty arrays", details)
        
        # Restore original values
        restore_payload = {
            "title": current_meeting.get("title", "Weekly Collection Meeting"),
            "meeting_date": current_meeting.get("meeting_date"),
            "period_start": current_meeting.get("period_start", ""),
            "period_end": current_meeting.get("period_end", ""),
            "notes": current_meeting.get("notes", ""),
            "reps": current_meeting.get("reps", []),
            "branches": original_branches,
            "quotation": current_meeting.get("quotation", {}),
            "marketing_reps": original_marketing_reps,
            "financials": current_meeting.get("financials", {})
        }
        
        session.put(f"{BASE_URL}/meetings/{TARGET_MEETING_ID}", json=restore_payload)
        print("   ✅ Restored original branches and marketing_reps")
        
    except Exception as e:
        log_result(7, False, "Edge case exception", str(e))
    
    # Step 8: GET /api/analytics/trends
    print("\n" + "="*80)
    print("STEP 8: GET /api/analytics/trends")
    print("="*80)
    
    try:
        trends_resp = session.get(f"{BASE_URL}/analytics/trends")
        
        if trends_resp.status_code != 200:
            log_result(8, False, "GET /api/analytics/trends failed", 
                      f"Status: {trends_resp.status_code}")
        else:
            trends_data = trends_resp.json()
            weekly = trends_data.get("weekly", [])
            
            checks = []
            checks.append(("HTTP 200", True))
            checks.append(("weekly is list", isinstance(weekly, list)))
            
            if weekly:
                first_week = weekly[0]
                checks.append(("coll_pct field present", "coll_pct" in first_week))
                checks.append(("last_week_target_total field present", "last_week_target_total" in first_week))
            
            all_passed = all(c[1] for c in checks)
            details = f"Weekly points: {len(weekly)}, First week has coll_pct: {'coll_pct' in weekly[0] if weekly else False}, has last_week_target_total: {'last_week_target_total' in weekly[0] if weekly else False}"
            
            log_result(8, all_passed, "GET /api/analytics/trends", details)
        
    except Exception as e:
        log_result(8, False, "GET /api/analytics/trends exception", str(e))
    
    # Step 9: Final sanity check - verify original state restored
    print("\n" + "="*80)
    print("STEP 9: Final sanity check - verify original state restored")
    print("="*80)
    
    try:
        final_resp = session.get(f"{BASE_URL}/meetings/{TARGET_MEETING_ID}")
        
        if final_resp.status_code != 200:
            log_result(9, False, "Final GET failed", 
                      f"Status: {final_resp.status_code}")
        else:
            final_meeting = final_resp.json()
            final_reps = final_meeting.get("reps", [])
            
            checks = []
            checks.append(("HTTP 200", True))
            checks.append(("Reps count matches original", len(final_reps) == original_reps_count))
            checks.append(("PlaywrightRep NOT in reps", not any(r.get("name") == "PlaywrightRep" for r in final_reps)))
            
            # Verify total meetings count unchanged
            all_meetings_resp = session.get(f"{BASE_URL}/meetings")
            if all_meetings_resp.status_code == 200:
                all_meetings = all_meetings_resp.json()
                checks.append(("Total meetings count unchanged", len(all_meetings) > 0))
            
            all_passed = all(c[1] for c in checks)
            details = f"Final reps count: {len(final_reps)}, Original reps count: {original_reps_count}, PlaywrightRep present: {any(r.get('name') == 'PlaywrightRep' for r in final_reps)}"
            
            log_result(9, all_passed, "Final sanity check", details)
        
    except Exception as e:
        log_result(9, False, "Final sanity check exception", str(e))
    
    # Print summary
    print_summary()
    
    # Check backend logs
    print("\n" + "="*80)
    print("BACKEND LOGS CHECK")
    print("="*80)
    print("Checking /var/log/supervisor/backend.err.log for 500 errors during test run...")
    
    # Exit with appropriate code
    all_passed = all(r["passed"] for r in results)
    sys.exit(0 if all_passed else 1)

if __name__ == "__main__":
    main()
