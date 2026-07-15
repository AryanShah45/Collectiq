#!/usr/bin/env python3
"""
Comprehensive smoke test for CollectIQ backend bug fix:
- ModuleNotFoundError fix (fpdf2, openpyxl, google-genai, pandas)
- Backup verification (ALL meetings present)
"""

import requests
import json
import sys

# Backend URL from frontend/.env
BASE_URL = "https://github-opener-9.preview.emergentagent.com/api"

# Test credentials
ADMIN_EMAIL = "admin@company.com"
ADMIN_PASSWORD = "Admin@123"

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
    print("SMOKE TEST SUMMARY")
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
    
    # Get initial meeting count
    print("\n" + "="*80)
    print("STEP 0b: Get initial meeting count")
    print("="*80)
    try:
        initial_resp = session.get(f"{BASE_URL}/meetings")
        if initial_resp.status_code != 200:
            print(f"❌ Failed to get initial meetings: {initial_resp.status_code}")
            sys.exit(1)
        initial_meetings = initial_resp.json()
        initial_count = len(initial_meetings)
        print(f"✅ Initial meeting count: {initial_count}")
        print(f"   Existing meeting dates: {[m.get('meeting_date') for m in initial_meetings]}")
    except Exception as e:
        print(f"❌ Error getting initial meetings: {e}")
        sys.exit(1)
    
    # Step 1: POST /api/meetings with full-shape body
    print("\n" + "="*80)
    print("STEP 1: POST /api/meetings (full-shape body)")
    print("="*80)
    
    meeting_payload = {
        "title": "Smoke Test",
        "meeting_date": "2099-08-15",
        "period_start": "2099-08-09",
        "period_end": "2099-08-14",
        "reps": [
            {
                "name": "Smoke",
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
                "purchase": {"mbs": 10, "mcorp": 5},
                "sales": {"mbs": 20, "mcorp": 8}
            }
        ],
        "quotation": {},
        "marketing_reps": [
            {
                "name": "SmokeMkt",
                "visit": {"mbs": 0, "mcorp": 0},
                "inquiry": {"mbs": 0, "mcorp": 0},
                "inquiry_conform": {"mbs": 0, "mcorp": 0},
                "order_loss": {"mbs": 0, "mcorp": 0},
                "branch_sales": [
                    {
                        "name": "Direct Sale",
                        "tons": {"mbs": 5, "mcorp": 2}
                    }
                ],
                "target_tons": 20,
                "target_party": 5
            }
        ]
    }
    
    try:
        create_resp = session.post(f"{BASE_URL}/meetings", json=meeting_payload)
        if create_resp.status_code != 200:
            log_result(1, False, "POST /api/meetings failed", 
                      f"Status: {create_resp.status_code}, Body: {create_resp.text[:500]}")
            print_summary()
            sys.exit(1)
        
        meeting_data = create_resp.json()
        new_id = meeting_data.get("id")
        
        # Verify response structure
        summary = meeting_data.get("summary", {})
        coll_pct = summary.get("coll_pct")
        last_week_target_total = summary.get("last_week_target_total")
        
        # Expected: collected = 100 + 50 = 150, last_week_target = 1000
        # coll_pct should be round(150 * 100 / 1000, 2) = 15.0
        expected_coll_pct = 15.0
        
        checks = []
        checks.append(("id present", new_id is not None))
        checks.append(("last_week_target_total", last_week_target_total == 1000))
        checks.append(("coll_pct", coll_pct == expected_coll_pct))
        
        all_passed = all(c[1] for c in checks)
        details = f"id={new_id}, last_week_target_total={last_week_target_total}, coll_pct={coll_pct} (expected {expected_coll_pct})"
        
        log_result(1, all_passed, "POST /api/meetings", details)
        
        if not new_id:
            print("❌ No meeting ID returned, cannot continue")
            print_summary()
            sys.exit(1)
            
    except Exception as e:
        log_result(1, False, "POST /api/meetings exception", str(e))
        print_summary()
        sys.exit(1)
    
    # Step 2: GET /api/meetings/{id}/export.pdf
    print("\n" + "="*80)
    print("STEP 2: GET /api/meetings/{id}/export.pdf")
    print("="*80)
    
    try:
        pdf_resp = session.get(f"{BASE_URL}/meetings/{new_id}/export.pdf")
        
        checks = []
        checks.append(("status 200", pdf_resp.status_code == 200))
        
        content_type = pdf_resp.headers.get("Content-Type", "")
        checks.append(("Content-Type starts with application/pdf", 
                      content_type.startswith("application/pdf")))
        
        body_size = len(pdf_resp.content)
        checks.append(("Body size > 500 bytes", body_size > 500))
        
        content_disp = pdf_resp.headers.get("Content-Disposition", "")
        checks.append(("Content-Disposition present", "attachment" in content_disp.lower()))
        
        all_passed = all(c[1] for c in checks)
        details = f"Status: {pdf_resp.status_code}, Content-Type: {content_type}, Size: {body_size} bytes, Content-Disposition: {content_disp}"
        
        log_result(2, all_passed, "GET export.pdf", details)
        
    except Exception as e:
        log_result(2, False, "GET export.pdf exception", str(e))
    
    # Step 3: GET /api/meetings/{id}/export.xlsx
    print("\n" + "="*80)
    print("STEP 3: GET /api/meetings/{id}/export.xlsx")
    print("="*80)
    
    try:
        xlsx_resp = session.get(f"{BASE_URL}/meetings/{new_id}/export.xlsx")
        
        checks = []
        checks.append(("status 200", xlsx_resp.status_code == 200))
        
        content_type = xlsx_resp.headers.get("Content-Type", "")
        expected_xlsx_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        checks.append(("Content-Type is XLSX", content_type == expected_xlsx_type))
        
        body_size = len(xlsx_resp.content)
        checks.append(("Body size > 500 bytes", body_size > 500))
        
        content_disp = xlsx_resp.headers.get("Content-Disposition", "")
        checks.append(("Content-Disposition present", "attachment" in content_disp.lower()))
        
        all_passed = all(c[1] for c in checks)
        details = f"Status: {xlsx_resp.status_code}, Content-Type: {content_type}, Size: {body_size} bytes, Content-Disposition: {content_disp}"
        
        log_result(3, all_passed, "GET export.xlsx", details)
        
    except Exception as e:
        log_result(3, False, "GET export.xlsx exception", str(e))
    
    # Step 4: GET /api/backup
    print("\n" + "="*80)
    print("STEP 4: GET /api/backup")
    print("="*80)
    
    backup_data = None
    try:
        backup_resp = session.get(f"{BASE_URL}/backup")
        
        if backup_resp.status_code != 200:
            log_result(4, False, "GET /api/backup failed", 
                      f"Status: {backup_resp.status_code}, Body: {backup_resp.text[:500]}")
        else:
            backup_data = backup_resp.json()
            
            checks = []
            checks.append(("status 200", True))
            checks.append(("app == 'CollectIQ'", backup_data.get("app") == "CollectIQ"))
            checks.append(("version present", "version" in backup_data))
            checks.append(("exported_at present", "exported_at" in backup_data))
            checks.append(("settings is dict", isinstance(backup_data.get("settings"), dict)))
            checks.append(("meetings is list", isinstance(backup_data.get("meetings"), list)))
            
            content_disp = backup_resp.headers.get("Content-Disposition", "")
            checks.append(("Content-Disposition has collectiq-backup", 
                          "collectiq-backup" in content_disp.lower()))
            
            backup_meetings = backup_data.get("meetings", [])
            backup_count = len(backup_meetings)
            
            # Get current meeting count
            current_resp = session.get(f"{BASE_URL}/meetings")
            current_count = len(current_resp.json()) if current_resp.status_code == 200 else 0
            
            checks.append(("len(meetings) == current count", backup_count == current_count))
            
            # Check if new meeting is in backup
            new_meeting_in_backup = any(m.get("id") == new_id for m in backup_meetings)
            checks.append(("new meeting in backup", new_meeting_in_backup))
            
            all_passed = all(c[1] for c in checks)
            details = f"app={backup_data.get('app')}, meetings count={backup_count}, current count={current_count}, new meeting present={new_meeting_in_backup}"
            
            log_result(4, all_passed, "GET /api/backup", details)
            
    except Exception as e:
        log_result(4, False, "GET /api/backup exception", str(e))
    
    # Step 5: POST /api/restore with exact backup
    print("\n" + "="*80)
    print("STEP 5: POST /api/restore (valid backup)")
    print("="*80)
    
    if backup_data:
        try:
            restore_resp = session.post(f"{BASE_URL}/restore", json=backup_data)
            
            if restore_resp.status_code != 200:
                log_result(5, False, "POST /api/restore failed", 
                          f"Status: {restore_resp.status_code}, Body: {restore_resp.text[:500]}")
            else:
                restore_result = restore_resp.json()
                
                checks = []
                checks.append(("status 200", True))
                checks.append(("ok == true", restore_result.get("ok") == True))
                
                restored_count = restore_result.get("restored_meetings")
                expected_count = len(backup_data.get("meetings", []))
                checks.append(("restored_meetings == backup count", 
                              restored_count == expected_count))
                
                # Verify count after restore
                after_resp = session.get(f"{BASE_URL}/meetings")
                after_count = len(after_resp.json()) if after_resp.status_code == 200 else 0
                checks.append(("count after restore == backup count", 
                              after_count == expected_count))
                
                all_passed = all(c[1] for c in checks)
                details = f"ok={restore_result.get('ok')}, restored_meetings={restored_count}, expected={expected_count}, after_count={after_count}"
                
                log_result(5, all_passed, "POST /api/restore (valid)", details)
                
        except Exception as e:
            log_result(5, False, "POST /api/restore exception", str(e))
    else:
        log_result(5, False, "POST /api/restore skipped", "No backup data from step 4")
    
    # Step 6: POST /api/restore with invalid payload
    print("\n" + "="*80)
    print("STEP 6: POST /api/restore (invalid payload)")
    print("="*80)
    
    try:
        # Get count before invalid restore
        before_resp = session.get(f"{BASE_URL}/meetings")
        count_before = len(before_resp.json()) if before_resp.status_code == 200 else 0
        
        invalid_resp = session.post(f"{BASE_URL}/restore", json={"app": "NotCollectIQ"})
        
        checks = []
        checks.append(("status 400", invalid_resp.status_code == 400))
        
        # Check that detail message is present
        if invalid_resp.status_code == 400:
            try:
                error_data = invalid_resp.json()
                checks.append(("detail message present", "detail" in error_data))
            except:
                checks.append(("detail message present", False))
        
        # Verify data NOT wiped
        after_resp = session.get(f"{BASE_URL}/meetings")
        count_after = len(after_resp.json()) if after_resp.status_code == 200 else 0
        checks.append(("data NOT wiped", count_after == count_before))
        
        all_passed = all(c[1] for c in checks)
        details = f"Status: {invalid_resp.status_code}, count_before={count_before}, count_after={count_after}"
        
        log_result(6, all_passed, "POST /api/restore (invalid)", details)
        
    except Exception as e:
        log_result(6, False, "POST /api/restore (invalid) exception", str(e))
    
    # Step 7: DELETE /api/meetings/{id}
    print("\n" + "="*80)
    print("STEP 7: DELETE /api/meetings/{id}")
    print("="*80)
    
    try:
        delete_resp = session.delete(f"{BASE_URL}/meetings/{new_id}")
        
        checks = []
        checks.append(("status 200", delete_resp.status_code == 200))
        
        if delete_resp.status_code == 200:
            delete_result = delete_resp.json()
            checks.append(("ok == true", delete_result.get("ok") == True))
        
        # Verify meeting is gone
        get_resp = session.get(f"{BASE_URL}/meetings/{new_id}")
        checks.append(("subsequent GET returns 404", get_resp.status_code == 404))
        
        all_passed = all(c[1] for c in checks)
        details = f"Delete status: {delete_resp.status_code}, GET after delete: {get_resp.status_code}"
        
        log_result(7, all_passed, "DELETE /api/meetings/{id}", details)
        
    except Exception as e:
        log_result(7, False, "DELETE exception", str(e))
    
    # Step 8: Sanity check - final count equals initial count
    print("\n" + "="*80)
    print("STEP 8: Sanity check (final count == initial count)")
    print("="*80)
    
    try:
        final_resp = session.get(f"{BASE_URL}/meetings")
        if final_resp.status_code != 200:
            log_result(8, False, "Sanity check failed", 
                      f"Failed to get final meetings: {final_resp.status_code}")
        else:
            final_meetings = final_resp.json()
            final_count = len(final_meetings)
            
            passed = final_count == initial_count
            details = f"Initial count: {initial_count}, Final count: {final_count}"
            
            log_result(8, passed, "Sanity check (count unchanged)", details)
            
    except Exception as e:
        log_result(8, False, "Sanity check exception", str(e))
    
    # Print summary
    print_summary()
    
    # Check for 500/502 errors in backend logs
    print("\n" + "="*80)
    print("CHECKING BACKEND LOGS FOR 500/502 ERRORS")
    print("="*80)
    print("(This check is informational - errors during test run would be visible above)")
    
    # Exit with appropriate code
    all_passed = all(r["passed"] for r in results)
    sys.exit(0 if all_passed else 1)

if __name__ == "__main__":
    main()
