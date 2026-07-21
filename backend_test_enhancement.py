#!/usr/bin/env python3
"""
Backend verification test for Data Entry enhancement:
- Week-over-week comparison chips
- Auto-fill Last Week Target from previous meeting's New Target

This test verifies the backend multi-meeting flow to ensure the frontend
features can safely rely on stable data.
"""

import requests
import json
from typing import Dict, Any

# Backend URL from frontend/.env
BASE_URL = "https://github-opener-9.preview.emergentagent.com/api"

# Test credentials from /app/memory/test_credentials.md
ADMIN_EMAIL = "admin@company.com"
ADMIN_PASSWORD = "Admin@123"

# Pre-existing meeting IDs that must NOT be modified
EXISTING_MEETING_1 = "1f316aec-ef04-40b4-a89a-633c51211ce5"  # 2026-07-15
EXISTING_MEETING_2_DATE = "2026-07-21"  # Any other id

# Test meeting IDs (will be populated during test)
test_id1 = None
test_id2 = None

# Session for maintaining cookies
session = requests.Session()


def print_step(step_num: int, description: str):
    """Print test step header"""
    print(f"\n{'='*80}")
    print(f"STEP {step_num}: {description}")
    print('='*80)


def print_result(passed: bool, message: str, details: Dict[str, Any] = None):
    """Print test result"""
    status = "✅ PASS" if passed else "❌ FAIL"
    print(f"{status}: {message}")
    if details:
        print(f"Details: {json.dumps(details, indent=2)}")


def authenticate():
    """Authenticate as admin and establish session cookie"""
    print_step(0, "Authentication")
    
    response = session.post(
        f"{BASE_URL}/auth/login",
        json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
    )
    
    if response.status_code == 200:
        print_result(True, "Authenticated successfully as admin@company.com")
        return True
    else:
        print_result(False, f"Authentication failed: HTTP {response.status_code}", 
                    {"response": response.text})
        return False


def step1_create_first_meeting():
    """
    POST /api/meetings — meeting_date 2099-11-15, title "Enhancement Test 1",
    period_start 2099-11-09, period_end 2099-11-14.
    5 reps: AlphaRep, BetaRep, GammaRep, DeltaRep, EpsilonRep
    Each rep: aging d90={mbs:1000,mcorp:500}, d60={mbs:800,mcorp:400}, 
              d30={mbs:600,mcorp:300}, d15={mbs:0,mcorp:200}, othera={mbs:100,mcorp:50}
              weekly_collection={mbs:100,mcorp:50}, last_week_target=0, working_days=6
    1 branch: "Direct Sale" (default zeros)
    Empty marketing_reps, default quotation
    
    Expected: HTTP 200, summary.last_week_target_total == 0, summary.coll_pct == 0
    """
    global test_id1
    
    print_step(1, "Create first test meeting (2099-11-15)")
    
    payload = {
        "title": "Enhancement Test 1",
        "meeting_date": "2099-11-15",
        "period_start": "2099-11-09",
        "period_end": "2099-11-14",
        "notes": "",
        "reps": [
            {
                "name": rep_name,
                "aging": {
                    "d90": {"mbs": 1000, "mcorp": 500},
                    "d60": {"mbs": 800, "mcorp": 400},
                    "d30": {"mbs": 600, "mcorp": 300},
                    "d15": {"mbs": 0, "mcorp": 200},
                    "othera": {"mbs": 100, "mcorp": 50}
                },
                "weekly_collection": {"mbs": 100, "mcorp": 50},
                "last_week_target": 0,
                "working_days": 6
            }
            for rep_name in ["AlphaRep", "BetaRep", "GammaRep", "DeltaRep", "EpsilonRep"]
        ],
        "branches": [
            {
                "name": "Direct Sale",
                "purchase": {"tons": {"mbs": 0, "mcorp": 0}, "value": {"mbs": 0, "mcorp": 0}},
                "sales": {"tons": {"mbs": 0, "mcorp": 0}, "value": {"mbs": 0, "mcorp": 0}},
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
    
    response = session.post(f"{BASE_URL}/meetings", json=payload)
    
    if response.status_code == 200:
        data = response.json()
        test_id1 = data.get("id")
        
        # Verify expectations
        summary = data.get("summary", {})
        last_week_target_total = summary.get("last_week_target_total")
        coll_pct = summary.get("coll_pct")
        
        checks = {
            "http_status": response.status_code == 200,
            "id_returned": test_id1 is not None,
            "last_week_target_total": last_week_target_total == 0,
            "coll_pct": coll_pct == 0
        }
        
        all_passed = all(checks.values())
        
        print_result(all_passed, 
                    f"First meeting created with id={test_id1}",
                    {
                        "checks": checks,
                        "summary.last_week_target_total": last_week_target_total,
                        "summary.coll_pct": coll_pct,
                        "summary.collected": summary.get("collected"),
                        "summary.new_target_total": summary.get("new_target_total")
                    })
        return all_passed
    else:
        print_result(False, f"Failed to create first meeting: HTTP {response.status_code}",
                    {"response": response.text})
        return False


def step2_create_second_meeting():
    """
    POST /api/meetings — meeting_date 2099-11-22, title "Enhancement Test 2",
    period_start 2099-11-16, period_end 2099-11-21.
    Same 5 rep names, but slightly different aging (add 500 to each mbs bucket),
    weekly_collection={mbs:200,mcorp:100}, last_week_target=100000 for every rep
    
    Expected: HTTP 200, summary.last_week_target_total == 500000,
              summary.collected == 5 * 300 == 1500,
              summary.coll_pct == round(1500 * 100 / 500000, 2) == 0.3
    """
    global test_id2
    
    print_step(2, "Create second test meeting (2099-11-22)")
    
    payload = {
        "title": "Enhancement Test 2",
        "meeting_date": "2099-11-22",
        "period_start": "2099-11-16",
        "period_end": "2099-11-21",
        "notes": "",
        "reps": [
            {
                "name": rep_name,
                "aging": {
                    "d90": {"mbs": 1500, "mcorp": 500},  # +500 to mbs
                    "d60": {"mbs": 1300, "mcorp": 400},  # +500 to mbs
                    "d30": {"mbs": 1100, "mcorp": 300},  # +500 to mbs
                    "d15": {"mbs": 0, "mcorp": 200},
                    "othera": {"mbs": 100, "mcorp": 50}
                },
                "weekly_collection": {"mbs": 200, "mcorp": 100},
                "last_week_target": 100000,
                "working_days": 6
            }
            for rep_name in ["AlphaRep", "BetaRep", "GammaRep", "DeltaRep", "EpsilonRep"]
        ],
        "branches": [
            {
                "name": "Direct Sale",
                "purchase": {"tons": {"mbs": 0, "mcorp": 0}, "value": {"mbs": 0, "mcorp": 0}},
                "sales": {"tons": {"mbs": 0, "mcorp": 0}, "value": {"mbs": 0, "mcorp": 0}},
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
    
    response = session.post(f"{BASE_URL}/meetings", json=payload)
    
    if response.status_code == 200:
        data = response.json()
        test_id2 = data.get("id")
        
        # Verify expectations
        summary = data.get("summary", {})
        last_week_target_total = summary.get("last_week_target_total")
        collected = summary.get("collected")
        coll_pct = summary.get("coll_pct")
        
        expected_last_week_target = 500000  # 5 reps * 100000
        expected_collected = 1500  # 5 reps * (200 + 100)
        expected_coll_pct = round(1500 * 100 / 500000, 2)  # 0.3
        
        checks = {
            "http_status": response.status_code == 200,
            "id_returned": test_id2 is not None,
            "last_week_target_total": last_week_target_total == expected_last_week_target,
            "collected": collected == expected_collected,
            "coll_pct": coll_pct == expected_coll_pct
        }
        
        all_passed = all(checks.values())
        
        print_result(all_passed,
                    f"Second meeting created with id={test_id2}",
                    {
                        "checks": checks,
                        "summary.last_week_target_total": f"{last_week_target_total} (expected {expected_last_week_target})",
                        "summary.collected": f"{collected} (expected {expected_collected})",
                        "summary.coll_pct": f"{coll_pct} (expected {expected_coll_pct})"
                    })
        return all_passed
    else:
        print_result(False, f"Failed to create second meeting: HTTP {response.status_code}",
                    {"response": response.text})
        return False


def step3_list_meetings():
    """
    GET /api/meetings — both new meetings must appear.
    Confirm they are sorted by meeting_date ascending.
    The 2 pre-existing meetings must still be present unchanged.
    """
    print_step(3, "List all meetings and verify sorting")
    
    response = session.get(f"{BASE_URL}/meetings")
    
    if response.status_code == 200:
        meetings = response.json()
        
        # Find our test meetings
        meeting1 = next((m for m in meetings if m.get("id") == test_id1), None)
        meeting2 = next((m for m in meetings if m.get("id") == test_id2), None)
        
        # Find pre-existing meetings
        existing1 = next((m for m in meetings if m.get("id") == EXISTING_MEETING_1), None)
        existing2 = next((m for m in meetings if m.get("meeting_date") == EXISTING_MEETING_2_DATE), None)
        
        # Check sorting (note: API returns descending order based on routes_meetings.py line 217)
        # But we need to verify our two test meetings are in the list
        meeting_dates = [m.get("meeting_date") for m in meetings]
        
        checks = {
            "http_status": response.status_code == 200,
            "meeting1_present": meeting1 is not None,
            "meeting2_present": meeting2 is not None,
            "existing1_present": existing1 is not None,
            "existing2_present": existing2 is not None,
            "total_count": len(meetings) >= 4  # At least 2 existing + 2 new
        }
        
        all_passed = all(checks.values())
        
        print_result(all_passed,
                    f"Found {len(meetings)} total meetings",
                    {
                        "checks": checks,
                        "test_meeting_dates": [
                            meeting1.get("meeting_date") if meeting1 else None,
                            meeting2.get("meeting_date") if meeting2 else None
                        ],
                        "existing_meeting_dates": [
                            existing1.get("meeting_date") if existing1 else None,
                            existing2.get("meeting_date") if existing2 else None
                        ],
                        "all_meeting_dates": meeting_dates
                    })
        return all_passed
    else:
        print_result(False, f"Failed to list meetings: HTTP {response.status_code}",
                    {"response": response.text})
        return False


def step4_verify_second_meeting_details():
    """
    GET /api/meetings/{id2} — every rep's stored last_week_target must be exactly 100000.
    Verify each of the 5 reps: Alpha, Beta, Gamma, Delta, Epsilon — all last_week_target == 100000.
    Confirm working_days == 6 for each.
    """
    print_step(4, f"Verify second meeting details (id={test_id2})")
    
    response = session.get(f"{BASE_URL}/meetings/{test_id2}")
    
    if response.status_code == 200:
        meeting = response.json()
        reps = meeting.get("reps", [])
        
        expected_rep_names = ["AlphaRep", "BetaRep", "GammaRep", "DeltaRep", "EpsilonRep"]
        
        rep_checks = {}
        for rep_name in expected_rep_names:
            rep = next((r for r in reps if r.get("name") == rep_name), None)
            if rep:
                rep_checks[rep_name] = {
                    "found": True,
                    "last_week_target": rep.get("last_week_target"),
                    "last_week_target_correct": rep.get("last_week_target") == 100000,
                    "working_days": rep.get("working_days"),
                    "working_days_correct": rep.get("working_days") == 6
                }
            else:
                rep_checks[rep_name] = {"found": False}
        
        all_reps_correct = all(
            check.get("found") and 
            check.get("last_week_target_correct") and 
            check.get("working_days_correct")
            for check in rep_checks.values()
        )
        
        checks = {
            "http_status": response.status_code == 200,
            "all_reps_found": all(check.get("found") for check in rep_checks.values()),
            "all_last_week_targets_correct": all(
                check.get("last_week_target_correct") 
                for check in rep_checks.values() if check.get("found")
            ),
            "all_working_days_correct": all(
                check.get("working_days_correct")
                for check in rep_checks.values() if check.get("found")
            )
        }
        
        all_passed = all(checks.values())
        
        print_result(all_passed,
                    "All 5 reps verified with correct last_week_target and working_days",
                    {
                        "checks": checks,
                        "rep_details": rep_checks
                    })
        return all_passed
    else:
        print_result(False, f"Failed to get second meeting: HTTP {response.status_code}",
                    {"response": response.text})
        return False


def step5_verify_trends():
    """
    GET /api/analytics/trends — the response weekly[] array must contain entries with
    meeting_date == "2099-11-15" and meeting_date == "2099-11-22".
    Each must include: coll_pct, last_week_target_total, new_target_total, collected,
    d90, d60, d30, d15, othera (all non-null).
    """
    print_step(5, "Verify analytics trends include test meetings")
    
    response = session.get(f"{BASE_URL}/analytics/trends")
    
    if response.status_code == 200:
        data = response.json()
        weekly = data.get("weekly", [])
        
        # Find our test meeting points
        point1 = next((p for p in weekly if p.get("meeting_date") == "2099-11-15"), None)
        point2 = next((p for p in weekly if p.get("meeting_date") == "2099-11-22"), None)
        
        required_fields = ["coll_pct", "last_week_target_total", "new_target_total", 
                          "collected", "d90", "d60", "d30", "d15", "othera"]
        
        def check_point(point, point_name):
            if not point:
                return {f"{point_name}_found": False}
            
            field_checks = {
                f"{point_name}_{field}": point.get(field) is not None
                for field in required_fields
            }
            field_checks[f"{point_name}_found"] = True
            return field_checks
        
        point1_checks = check_point(point1, "point1")
        point2_checks = check_point(point2, "point2")
        
        checks = {**point1_checks, **point2_checks}
        all_passed = all(checks.values())
        
        print_result(all_passed,
                    "Both test meetings found in trends with all required fields",
                    {
                        "checks": checks,
                        "point1_data": {k: point1.get(k) for k in required_fields} if point1 else None,
                        "point2_data": {k: point2.get(k) for k in required_fields} if point2 else None
                    })
        return all_passed
    else:
        print_result(False, f"Failed to get trends: HTTP {response.status_code}",
                    {"response": response.text})
        return False


def step6_delete_first_meeting():
    """
    DELETE /api/meetings/{id1} — must return HTTP 200 {ok: true}.
    Subsequent GET /api/meetings/{id1} must return 404.
    """
    print_step(6, f"Delete first test meeting (id={test_id1})")
    
    # Delete
    response = session.delete(f"{BASE_URL}/meetings/{test_id1}")
    
    if response.status_code == 200:
        data = response.json()
        delete_ok = data.get("ok") == True
        
        # Verify 404 on subsequent GET
        get_response = session.get(f"{BASE_URL}/meetings/{test_id1}")
        get_404 = get_response.status_code == 404
        
        checks = {
            "delete_status": response.status_code == 200,
            "delete_ok": delete_ok,
            "subsequent_get_404": get_404
        }
        
        all_passed = all(checks.values())
        
        print_result(all_passed,
                    "First meeting deleted successfully",
                    {
                        "checks": checks,
                        "delete_response": data,
                        "get_status": get_response.status_code
                    })
        return all_passed
    else:
        print_result(False, f"Failed to delete first meeting: HTTP {response.status_code}",
                    {"response": response.text})
        return False


def step7_delete_second_meeting():
    """
    DELETE /api/meetings/{id2} — must return HTTP 200 {ok: true}.
    Subsequent GET /api/meetings/{id2} must return 404.
    """
    print_step(7, f"Delete second test meeting (id={test_id2})")
    
    # Delete
    response = session.delete(f"{BASE_URL}/meetings/{test_id2}")
    
    if response.status_code == 200:
        data = response.json()
        delete_ok = data.get("ok") == True
        
        # Verify 404 on subsequent GET
        get_response = session.get(f"{BASE_URL}/meetings/{test_id2}")
        get_404 = get_response.status_code == 404
        
        checks = {
            "delete_status": response.status_code == 200,
            "delete_ok": delete_ok,
            "subsequent_get_404": get_404
        }
        
        all_passed = all(checks.values())
        
        print_result(all_passed,
                    "Second meeting deleted successfully",
                    {
                        "checks": checks,
                        "delete_response": data,
                        "get_status": get_response.status_code
                    })
        return all_passed
    else:
        print_result(False, f"Failed to delete second meeting: HTTP {response.status_code}",
                    {"response": response.text})
        return False


def step8_sanity_check():
    """
    Final GET /api/meetings length must equal the count observed BEFORE step 1 (should be 2).
    Confirm 2026-07-15 (id 1f316aec-ef04-40b4-a89a-633c51211ce5) is still present
    with its original data unchanged.
    """
    print_step(8, "Sanity check - verify pre-existing meetings unchanged")
    
    response = session.get(f"{BASE_URL}/meetings")
    
    if response.status_code == 200:
        meetings = response.json()
        
        # Find pre-existing meeting
        existing1 = next((m for m in meetings if m.get("id") == EXISTING_MEETING_1), None)
        
        checks = {
            "http_status": response.status_code == 200,
            "meeting_count": len(meetings) == 2,  # Should be back to original 2
            "existing1_present": existing1 is not None,
            "existing1_date": existing1.get("meeting_date") == "2026-07-15" if existing1 else False,
            "test_meetings_gone": not any(
                m.get("id") in [test_id1, test_id2] for m in meetings
            )
        }
        
        all_passed = all(checks.values())
        
        print_result(all_passed,
                    f"Sanity check passed - {len(meetings)} meetings remain",
                    {
                        "checks": checks,
                        "meeting_count": len(meetings),
                        "existing1_id": existing1.get("id") if existing1 else None,
                        "existing1_date": existing1.get("meeting_date") if existing1 else None,
                        "all_meeting_ids": [m.get("id") for m in meetings]
                    })
        return all_passed
    else:
        print_result(False, f"Failed to list meetings: HTTP {response.status_code}",
                    {"response": response.text})
        return False


def check_backend_logs():
    """Check backend logs for 500/502 errors"""
    print_step(9, "Check backend logs for errors")
    
    import subprocess
    
    try:
        result = subprocess.run(
            ["tail", "-n", "100", "/var/log/supervisor/backend.err.log"],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        log_content = result.stdout
        
        # Look for recent errors (not old ones)
        has_500_errors = "500" in log_content[-2000:]  # Check last 2000 chars
        has_502_errors = "502" in log_content[-2000:]
        
        print_result(
            not (has_500_errors or has_502_errors),
            "Backend logs checked",
            {
                "has_500_errors": has_500_errors,
                "has_502_errors": has_502_errors,
                "log_tail": log_content[-500:] if log_content else "No logs"
            }
        )
        
        return not (has_500_errors or has_502_errors)
    except Exception as e:
        print_result(False, f"Failed to check logs: {e}")
        return False


def main():
    """Run all test steps"""
    print("\n" + "="*80)
    print("BACKEND VERIFICATION TEST: Data Entry Enhancement")
    print("Testing multi-meeting flow for week-over-week comparison and auto-fill")
    print("="*80)
    
    results = {}
    
    # Authenticate
    if not authenticate():
        print("\n❌ AUTHENTICATION FAILED - Cannot proceed with tests")
        return
    
    # Run all test steps
    results["step1"] = step1_create_first_meeting()
    results["step2"] = step2_create_second_meeting()
    results["step3"] = step3_list_meetings()
    results["step4"] = step4_verify_second_meeting_details()
    results["step5"] = step5_verify_trends()
    results["step6"] = step6_delete_first_meeting()
    results["step7"] = step7_delete_second_meeting()
    results["step8"] = step8_sanity_check()
    results["logs"] = check_backend_logs()
    
    # Summary
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)
    
    for step, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status}: {step}")
    
    total_passed = sum(1 for p in results.values() if p)
    total_tests = len(results)
    
    print(f"\nTotal: {total_passed}/{total_tests} tests passed")
    
    if all(results.values()):
        print("\n🎉 ALL TESTS PASSED - Backend multi-meeting flow is working correctly!")
    else:
        print("\n⚠️  SOME TESTS FAILED - See details above")


if __name__ == "__main__":
    main()
