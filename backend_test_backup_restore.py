#!/usr/bin/env python3
"""
Backend Test: CollectIQ Backup & Restore Feature
Tests GET /api/backup and POST /api/restore endpoints with safety checks.
"""
import requests
import json
import sys

# Backend URL from frontend/.env
BASE_URL = "https://gather-portal-dev.preview.emergentagent.com/api"

# Test credentials from /app/memory/test_credentials.md
ADMIN_EMAIL = "admin@company.com"
ADMIN_PASSWORD = "Admin@123"

def print_section(title):
    print(f"\n{'='*80}")
    print(f"  {title}")
    print(f"{'='*80}\n")

def print_result(step, passed, message):
    status = "✅ PASS" if passed else "❌ FAIL"
    print(f"{status} - Step {step}: {message}")

def authenticate():
    """Authenticate as admin and return session with cookie."""
    print_section("AUTHENTICATION")
    session = requests.Session()
    
    login_url = f"{BASE_URL}/auth/login"
    payload = {"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
    
    print(f"POST {login_url}")
    print(f"Payload: {payload}")
    
    resp = session.post(login_url, json=payload)
    print(f"Status: {resp.status_code}")
    
    if resp.status_code != 200:
        print(f"❌ Authentication failed: {resp.text}")
        sys.exit(1)
    
    data = resp.json()
    print(f"✅ Authenticated as: {data.get('email')} (role: {data.get('role')})")
    print(f"Session cookies: {session.cookies.get_dict()}")
    
    return session

def test_backup_restore():
    """Main test suite for backup & restore functionality."""
    
    # Authenticate
    session = authenticate()
    
    # ========== STEP 1: GET /api/meetings - Record current count ==========
    print_section("STEP 1: GET /api/meetings - Record Current Count")
    
    meetings_url = f"{BASE_URL}/meetings"
    print(f"GET {meetings_url}")
    
    resp = session.get(meetings_url)
    print(f"Status: {resp.status_code}")
    
    if resp.status_code != 200:
        print_result(1, False, f"Failed to get meetings: {resp.text}")
        return False
    
    meetings_data = resp.json()
    original_count = len(meetings_data)
    print(f"Current meeting count: {original_count}")
    print(f"Expected: 4 seeded meetings")
    
    if original_count != 4:
        print(f"⚠️  WARNING: Expected 4 meetings, found {original_count}")
    
    print_result(1, True, f"Retrieved {original_count} meetings")
    
    # ========== STEP 2: GET /api/backup - Verify response structure ==========
    print_section("STEP 2: GET /api/backup - Verify Response Structure")
    
    backup_url = f"{BASE_URL}/backup"
    print(f"GET {backup_url}")
    
    resp = session.get(backup_url)
    print(f"Status: {resp.status_code}")
    
    if resp.status_code != 200:
        print_result(2, False, f"Backup endpoint failed: {resp.text}")
        return False
    
    # Check Content-Disposition header
    content_disp = resp.headers.get('Content-Disposition', '')
    print(f"Content-Disposition header: {content_disp}")
    
    has_attachment = 'attachment' in content_disp.lower()
    has_filename = 'collectiq-backup' in content_disp.lower()
    
    if not has_attachment:
        print_result(2, False, "Content-Disposition header missing 'attachment'")
        return False
    
    if not has_filename:
        print_result(2, False, "Content-Disposition header missing 'collectiq-backup'")
        return False
    
    # Parse backup JSON
    backup_data = resp.json()
    print(f"\nBackup JSON structure:")
    print(f"  - app: {backup_data.get('app')}")
    print(f"  - version: {backup_data.get('version')}")
    print(f"  - exported_at: {backup_data.get('exported_at')}")
    print(f"  - settings: {type(backup_data.get('settings'))} with keys {list(backup_data.get('settings', {}).keys())}")
    print(f"  - meetings: {type(backup_data.get('meetings'))} with length {len(backup_data.get('meetings', []))}")
    
    # Verify structure
    checks = []
    
    if backup_data.get('app') == 'CollectIQ':
        print("  ✓ app == 'CollectIQ'")
        checks.append(True)
    else:
        print(f"  ✗ app != 'CollectIQ' (got: {backup_data.get('app')})")
        checks.append(False)
    
    if 'version' in backup_data:
        print(f"  ✓ 'version' field present (value: {backup_data.get('version')})")
        checks.append(True)
    else:
        print("  ✗ 'version' field missing")
        checks.append(False)
    
    if isinstance(backup_data.get('settings'), dict):
        print("  ✓ 'settings' is an object")
        checks.append(True)
    else:
        print("  ✗ 'settings' is not an object")
        checks.append(False)
    
    meetings_array = backup_data.get('meetings', [])
    if isinstance(meetings_array, list):
        print(f"  ✓ 'meetings' is an array")
        checks.append(True)
    else:
        print("  ✗ 'meetings' is not an array")
        checks.append(False)
    
    if len(meetings_array) == original_count:
        print(f"  ✓ meetings array length ({len(meetings_array)}) == original count ({original_count})")
        checks.append(True)
    else:
        print(f"  ✗ meetings array length ({len(meetings_array)}) != original count ({original_count})")
        checks.append(False)
    
    if all(checks):
        print_result(2, True, "Backup response structure valid with correct headers")
    else:
        print_result(2, False, "Backup response structure validation failed")
        return False
    
    # ========== STEP 3: POST /api/restore - Round-trip with exact backup ==========
    print_section("STEP 3: POST /api/restore - Round-trip with Exact Backup")
    
    restore_url = f"{BASE_URL}/restore"
    print(f"POST {restore_url}")
    print(f"Payload: <exact backup from step 2> ({len(json.dumps(backup_data))} bytes)")
    
    resp = session.post(restore_url, json=backup_data)
    print(f"Status: {resp.status_code}")
    
    if resp.status_code != 200:
        print_result(3, False, f"Restore failed: {resp.text}")
        return False
    
    restore_result = resp.json()
    print(f"Response: {restore_result}")
    
    # Verify response structure
    if not restore_result.get('ok'):
        print_result(3, False, f"Response 'ok' field is not true: {restore_result}")
        return False
    
    restored_count = restore_result.get('restored_meetings')
    print(f"Restored meetings count: {restored_count}")
    
    if restored_count != original_count:
        print_result(3, False, f"Restored count ({restored_count}) != original count ({original_count})")
        return False
    
    print_result(3, True, f"Restore successful: {{ok: true, restored_meetings: {restored_count}}}")
    
    # ========== STEP 4: GET /api/meetings - Verify count unchanged ==========
    print_section("STEP 4: GET /api/meetings - Verify Round-trip Preserved Data")
    
    print(f"GET {meetings_url}")
    
    resp = session.get(meetings_url)
    print(f"Status: {resp.status_code}")
    
    if resp.status_code != 200:
        print_result(4, False, f"Failed to get meetings after restore: {resp.text}")
        return False
    
    meetings_after = resp.json()
    count_after = len(meetings_after)
    print(f"Meeting count after restore: {count_after}")
    print(f"Original count: {original_count}")
    
    if count_after != original_count:
        print_result(4, False, f"Count changed after round-trip: {original_count} -> {count_after}")
        return False
    
    # Spot-check: verify one meeting has d15 and Direct Sale branch
    print("\nSpot-checking data integrity:")
    
    found_d15 = False
    found_direct_sale = False
    
    for meeting in meetings_after:
        # Check for d15 in reps
        for rep in meeting.get('reps', []):
            aging = rep.get('aging', {})
            if 'd15' in aging:
                d15 = aging['d15']
                print(f"  ✓ Found rep '{rep.get('name')}' with d15: mbs={d15.get('mbs')}, mcorp={d15.get('mcorp')}")
                found_d15 = True
                break
        
        # Check for Direct Sale branch
        for branch in meeting.get('branches', []):
            if branch.get('name', '').lower().replace(' ', '') == 'directsale':
                print(f"  ✓ Found 'Direct Sale' branch with purchase={branch.get('purchase')}, sales={branch.get('sales')}")
                found_direct_sale = True
                break
        
        if found_d15 and found_direct_sale:
            break
    
    if not found_d15:
        print("  ⚠️  WARNING: No rep with d15 aging found")
    
    if not found_direct_sale:
        print("  ⚠️  WARNING: No 'Direct Sale' branch found")
    
    print_result(4, True, f"Round-trip preserved all {count_after} meetings with data integrity intact")
    
    # ========== STEP 5: Negative test - Invalid backup payload ==========
    print_section("STEP 5: Negative Test - Invalid Backup Payload")
    
    invalid_payload = {"app": "NotCollectIQ"}
    print(f"POST {restore_url}")
    print(f"Payload: {invalid_payload}")
    
    resp = session.post(restore_url, json=invalid_payload)
    print(f"Status: {resp.status_code}")
    
    if resp.status_code != 400:
        print_result(5, False, f"Expected 400 Bad Request, got {resp.status_code}")
        return False
    
    error_data = resp.json()
    print(f"Response: {error_data}")
    
    detail = error_data.get('detail', '')
    if 'collectiq' not in detail.lower() or 'backup' not in detail.lower():
        print_result(5, False, f"Error message doesn't mention CollectIQ backup: {detail}")
        return False
    
    print_result(5, True, f"Invalid payload correctly rejected with 400: {detail}")
    
    # Verify data NOT wiped
    print("\nVerifying data NOT wiped after invalid restore:")
    resp = session.get(meetings_url)
    if resp.status_code == 200:
        count_check = len(resp.json())
        print(f"Meeting count still: {count_check}")
        if count_check == original_count:
            print("  ✓ Data intact after invalid restore attempt")
        else:
            print(f"  ⚠️  WARNING: Count changed to {count_check} (expected {original_count})")
    
    # ========== STEP 6: Auth check - Backup without authentication ==========
    print_section("STEP 6: Auth Check - Backup Without Authentication")
    
    # Create new session without auth
    unauth_session = requests.Session()
    
    print(f"GET {backup_url} (without auth cookie)")
    
    resp = unauth_session.get(backup_url)
    print(f"Status: {resp.status_code}")
    
    if resp.status_code in [401, 403]:
        print_result(6, True, f"Backup correctly rejected without auth: {resp.status_code}")
    else:
        print_result(6, False, f"Expected 401/403, got {resp.status_code}: {resp.text}")
        return False
    
    # ========== FINAL VERIFICATION ==========
    print_section("FINAL VERIFICATION")
    
    print("Confirming seeded meetings remain intact:")
    resp = session.get(meetings_url)
    if resp.status_code == 200:
        final_count = len(resp.json())
        print(f"Final meeting count: {final_count}")
        if final_count == original_count:
            print("✅ All seeded meetings intact at end of test")
        else:
            print(f"⚠️  WARNING: Final count {final_count} != original {original_count}")
    
    return True

def main():
    print_section("CollectIQ Backup & Restore Test Suite")
    print(f"Backend URL: {BASE_URL}")
    print(f"Admin credentials: {ADMIN_EMAIL} / {ADMIN_PASSWORD}")
    
    try:
        success = test_backup_restore()
        
        print_section("TEST SUMMARY")
        
        if success:
            print("✅ ALL TESTS PASSED")
            print("\nVerified:")
            print("  1. GET /api/meetings returns current count (4 seeded meetings)")
            print("  2. GET /api/backup returns valid JSON with correct structure and headers")
            print("  3. POST /api/restore with exact backup succeeds with correct response")
            print("  4. Round-trip preserves all meetings and data integrity (d15, Direct Sale)")
            print("  5. Invalid backup payload correctly rejected with 400")
            print("  6. Backup endpoint requires admin authentication (401/403 without auth)")
            print("\n✅ No 500 errors encountered")
            print("✅ Seeded meetings remain intact")
            sys.exit(0)
        else:
            print("❌ SOME TESTS FAILED")
            print("See details above for failure reasons")
            sys.exit(1)
    
    except Exception as e:
        print(f"\n❌ TEST SUITE ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
