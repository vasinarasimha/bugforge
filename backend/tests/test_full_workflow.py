"""
BugForge Full Workflow Production Readiness Test (Idempotent)
=============================================================
Handles pre-existing test data gracefully. Cleans up old data first,
then creates fresh records and tests all features end-to-end.
"""
import sys
import json
import time
import traceback
import requests

BASE = "http://localhost:8000/api"
SUPER_ADMIN_EMAIL = "vln@superadmin.in"
SUPER_ADMIN_PASS = "admin@123"

# Test data identifiers
TEST_COMPANY_NAME = "TestCo_AutoTest"
TEST_ADMIN_EMAIL = "testadmin_autotest@testco.in"
TEST_EMAILS = {
    "admin": "testadmin_autotest@testco.in",
    "dev": "testdev_auto@testco.in",
    "qa": "testqa_auto@testco.in",
    "reporter": "testreporter_auto@testco.in",
    "pm": "testpm_auto@testco.in",
    "tl": "testtl_auto@testco.in",
}

# Tracking IDs for cleanup
ids = {}
test_results = []
total_passed = 0
total_failed = 0
failure_details = []


def log_test(name, passed, detail=""):
    global total_passed, total_failed
    if passed:
        total_passed += 1
        print(f"  [PASS] {name}")
    else:
        total_failed += 1
        failure_details.append({"name": name, "detail": detail})
        print(f"  [FAIL] {name} -- {detail}")


def h(token):
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


def find_company_id(super_token, name):
    """Find company ID by name."""
    r = requests.get(f"{BASE}/super-admin/companies", headers=h(super_token))
    if r.status_code == 200:
        for c in r.json():
            if c.get("name") == name:
                return c.get("id")
    return None


def find_user_id_by_email(admin_token, email):
    """Find user ID by email."""
    r = requests.get(f"{BASE}/admin/users?search={email}", headers=h(admin_token))
    if r.status_code == 200:
        for u in r.json().get("data", []):
            if u.get("email") == email:
                return u.get("id")
    return None


def run_all_tests():
    global ids

    print("\n" + "=" * 70)
    print("  BUGFORGE FULL WORKFLOW PRODUCTION READINESS TEST")
    print("=" * 70)

    # ============================================================
    # 1. HEALTH CHECK
    # ============================================================
    print("\n>> 1. HEALTH CHECK")
    try:
        r = requests.get(f"{BASE}/health", timeout=10)
        log_test("Health check returns 200", r.status_code == 200)
        data = r.json()
        log_test("Health response has status=healthy", data.get("status") == "healthy")
    except Exception as e:
        log_test("Health check", False, str(e))
        print("  ABORT: Backend not reachable.")
        return

    # ============================================================
    # 2. AUTHENTICATION
    # ============================================================
    print("\n>> 2. AUTHENTICATION")

    r = requests.post(f"{BASE}/auth/login", json={"email": SUPER_ADMIN_EMAIL, "password": SUPER_ADMIN_PASS})
    log_test("Super Admin login returns 200", r.status_code == 200, f"status={r.status_code}")
    if r.status_code != 200:
        print("  ABORT: Cannot login as Super Admin.")
        return
    super_token = r.json().get("access_token")
    user = r.json().get("user", {})
    log_test("Super Admin token received", super_token is not None)
    log_test("Super Admin user data correct", user.get("email") == SUPER_ADMIN_EMAIL)
    roles = [ro.get("name") for ro in user.get("roles", [])]
    log_test("Super Admin has correct role", "Super Admin" in roles or user.get("role") == "Super Admin")

    # Bad login
    r = requests.post(f"{BASE}/auth/login", json={"email": "bad@email.com", "password": "wrong"})
    log_test("Invalid login returns 401", r.status_code == 401)

    # GET /auth/me
    r = requests.get(f"{BASE}/auth/me", headers=h(super_token))
    log_test("GET /auth/me returns 200", r.status_code == 200)
    if r.status_code == 200:
        log_test("GET /auth/me correct email", r.json().get("email") == SUPER_ADMIN_EMAIL)

    # Unauthenticated
    r = requests.get(f"{BASE}/auth/me")
    log_test("Unauthenticated returns 401/403", r.status_code in [401, 403])

    # ============================================================
    # 3. PRE-CLEANUP: Remove old test data if exists
    # ============================================================
    print("\n>> 3. PRE-CLEANUP (removing old test data)")
    existing_company_id = find_company_id(super_token, TEST_COMPANY_NAME)
    if existing_company_id:
        r = requests.delete(f"{BASE}/super-admin/companies/{existing_company_id}", headers=h(super_token))
        print(f"  Pre-cleanup: deleted old company {existing_company_id}: status={r.status_code}")
    else:
        print("  No old test data found.")

    # ============================================================
    # 4. SUPER ADMIN - COMPANY MANAGEMENT
    # ============================================================
    print("\n>> 4. SUPER ADMIN - COMPANY MANAGEMENT")

    # Create company
    company_data = {
        "name": TEST_COMPANY_NAME,
        "legal_name": "TestCo AutoTest Inc.",
        "timezone": "UTC",
        "admin": {
            "first_name": "TestAdmin",
            "last_name": "AutoTest",
            "email": TEST_ADMIN_EMAIL,
            "password": "TestPass@123",
            "job_title": "Company Administrator",
            "department": "IT",
        }
    }
    r = requests.post(f"{BASE}/super-admin/companies", json=company_data, headers=h(super_token))
    log_test("Create company returns 201", r.status_code == 201, f"status={r.status_code}, body={r.text[:300]}")
    if r.status_code == 201:
        cd = r.json()
        ids["company_id"] = cd.get("company", {}).get("id") or cd.get("id")
        ids["admin_user_id"] = cd.get("admin_user", {}).get("id")
    else:
        # Try to find it
        ids["company_id"] = find_company_id(super_token, TEST_COMPANY_NAME)
        # Reactivate if deactivated
        if ids["company_id"]:
            requests.patch(f"{BASE}/super-admin/companies/{ids['company_id']}/status?is_active=true", headers=h(super_token))

    log_test("Company ID resolved", ids.get("company_id") is not None)

    # List companies
    r = requests.get(f"{BASE}/super-admin/companies", headers=h(super_token))
    log_test("List companies returns 200", r.status_code == 200)
    if r.status_code == 200:
        log_test("Companies list is non-empty", len(r.json()) > 0)

    # Get company detail
    if ids.get("company_id"):
        r = requests.get(f"{BASE}/super-admin/companies/{ids['company_id']}", headers=h(super_token))
        log_test("Get company detail returns 200", r.status_code == 200)

    # Update company
    if ids.get("company_id"):
        r = requests.patch(
            f"{BASE}/super-admin/companies/{ids['company_id']}",
            json={"website": "https://testco-autotest.example.com"},
            headers=h(super_token),
        )
        log_test("Update company returns 200", r.status_code == 200, f"status={r.status_code}")

    # Company toggle status
    if ids.get("company_id"):
        r = requests.patch(f"{BASE}/super-admin/companies/{ids['company_id']}/status?is_active=true", headers=h(super_token))
        log_test("Toggle company status returns 200", r.status_code == 200)

    # Super Admin Dashboard
    r = requests.get(f"{BASE}/super-admin/dashboard", headers=h(super_token))
    log_test("Super Admin dashboard returns 200", r.status_code == 200)
    if r.status_code == 200:
        log_test("Dashboard has total_companies", "total_companies" in r.json())

    # Super Admin Analytics
    r = requests.get(f"{BASE}/super-admin/analytics", headers=h(super_token))
    log_test("Super Admin analytics returns 200", r.status_code == 200)

    # Audit logs
    if ids.get("company_id"):
        r = requests.get(f"{BASE}/super-admin/companies/{ids['company_id']}/audit-logs", headers=h(super_token))
        log_test("Company audit logs returns 200", r.status_code == 200)

    # ============================================================
    # 5. ADMIN LOGIN & EMPLOYEE MANAGEMENT
    # ============================================================
    print("\n>> 5. ADMIN LOGIN & EMPLOYEE MANAGEMENT")

    r = requests.post(f"{BASE}/auth/login", json={"email": TEST_ADMIN_EMAIL, "password": "TestPass@123"})
    log_test("Admin login returns 200", r.status_code == 200, f"status={r.status_code}")
    if r.status_code == 200:
        admin_token = r.json().get("access_token")
        log_test("Admin token received", admin_token is not None)
    else:
        print("  WARN: Admin login failed. Using Super Admin token.")
        admin_token = super_token

    # Roles
    r = requests.get(f"{BASE}/admin/roles", headers=h(admin_token))
    log_test("List roles returns 200", r.status_code == 200)
    if r.status_code == 200:
        log_test("Roles list is non-empty", len(r.json()) > 0)

    # Create employees
    employees = [
        {"full_name": "TestDev AutoTest", "email": TEST_EMAILS["dev"], "password": "DevPass@123", "role": "Developer"},
        {"full_name": "TestQA AutoTest", "email": TEST_EMAILS["qa"], "password": "QAPass@123", "role": "QA"},
        {"full_name": "TestReporter AutoTest", "email": TEST_EMAILS["reporter"], "password": "RepPass@123", "role": "Reporter"},
        {"full_name": "TestPM AutoTest", "email": TEST_EMAILS["pm"], "password": "PMPass@123", "role": "Project Manager"},
        {"full_name": "TestTL AutoTest", "email": TEST_EMAILS["tl"], "password": "TLPass@123", "role": "Team Leader"},
    ]
    for emp in employees:
        r = requests.post(f"{BASE}/admin/users", json=emp, headers=h(admin_token))
        role_key = emp["role"].lower().replace(" ", "_")
        if r.status_code == 201:
            ids[f"{role_key}_id"] = r.json().get("id")
            log_test(f"Create {emp['role']} returns 201", True)
        elif r.status_code == 409:
            # Already exists, find the ID and reactivate
            uid = find_user_id_by_email(admin_token, emp["email"])
            ids[f"{role_key}_id"] = uid
            if uid:
                requests.patch(f"{BASE}/admin/users/{uid}", json={"is_active": True, "password": emp["password"]}, headers=h(admin_token))
            log_test(f"Create {emp['role']} (already exists, ID resolved)", uid is not None, f"id={uid}")
        else:
            log_test(f"Create {emp['role']}", False, f"status={r.status_code}, body={r.text[:200]}")

    # List employees
    r = requests.get(f"{BASE}/admin/users", headers=h(admin_token))
    log_test("List employees returns 200", r.status_code == 200)
    if r.status_code == 200:
        log_test("Employees data non-empty", len(r.json().get("data", [])) > 0)

    # Admin stats
    r = requests.get(f"{BASE}/admin/stats", headers=h(admin_token))
    log_test("Admin stats returns 200", r.status_code == 200)

    # Get single employee
    if ids.get("developer_id"):
        r = requests.get(f"{BASE}/admin/users/{ids['developer_id']}", headers=h(admin_token))
        log_test("Get employee detail returns 200", r.status_code == 200)

    # Update employee
    if ids.get("developer_id"):
        r = requests.patch(
            f"{BASE}/admin/users/{ids['developer_id']}",
            json={"department": "Engineering", "job_title": "Senior Developer"},
            headers=h(admin_token),
        )
        log_test("Update employee returns 200", r.status_code == 200)

    # Self profile update
    r = requests.patch(f"{BASE}/auth/me", json={"department": "Management"}, headers=h(admin_token))
    log_test("Self profile update returns 200", r.status_code == 200)

    # ============================================================
    # 6. PROJECTS
    # ============================================================
    print("\n>> 6. PROJECTS")

    pm_id = ids.get("project_manager_id")
    tl_id = ids.get("team_leader_id")

    project_data = {
        "name": "AutoTest Project",
        "key": "ATP",
        "description": "Automated test project for production readiness",
        "status": "Active",
        "client_name": "Test Client",
        "tech_stack": "Python, React",
        "project_manager_id": pm_id,
        "team_leader_id": tl_id,
    }
    r = requests.post(f"{BASE}/projects", json=project_data, headers=h(admin_token))
    log_test("Create project returns 201", r.status_code == 201, f"status={r.status_code}, body={r.text[:300]}")
    if r.status_code == 201:
        ids["project_id"] = r.json().get("id")

    # List projects
    r = requests.get(f"{BASE}/projects", headers=h(admin_token))
    log_test("List projects returns 200", r.status_code == 200)
    if r.status_code == 200:
        projs = r.json()
        log_test("Projects list non-empty", len(projs) > 0)
        # If project wasn't created, find existing
        if not ids.get("project_id"):
            for p in projs:
                if p.get("name") == "AutoTest Project":
                    ids["project_id"] = p.get("id")
                    break

    # Get project
    if ids.get("project_id"):
        r = requests.get(f"{BASE}/projects/{ids['project_id']}", headers=h(admin_token))
        log_test("Get project detail returns 200", r.status_code == 200)

    # Update project
    if ids.get("project_id"):
        r = requests.put(
            f"{BASE}/projects/{ids['project_id']}",
            json={**project_data, "description": "Updated description for testing"},
            headers=h(admin_token),
        )
        log_test("Update project returns 200", r.status_code == 200, f"status={r.status_code}")

    # Project history
    if ids.get("project_id"):
        r = requests.get(f"{BASE}/projects/{ids['project_id']}/history", headers=h(admin_token))
        log_test("Get project history returns 200", r.status_code == 200)

    # ============================================================
    # 7. ISSUES
    # ============================================================
    print("\n>> 7. ISSUES")

    # Lookups
    r = requests.get(f"{BASE}/issues/statuses", headers=h(admin_token))
    log_test("List issue statuses returns 200", r.status_code == 200)
    statuses = r.json() if r.status_code == 200 else []
    status_id = statuses[0]["id"] if statuses else 1

    r = requests.get(f"{BASE}/issues/priorities", headers=h(admin_token))
    log_test("List issue priorities returns 200", r.status_code == 200)
    priorities = r.json() if r.status_code == 200 else []
    priority_id = priorities[0]["id"] if priorities else 1

    r = requests.get(f"{BASE}/issues/severities", headers=h(admin_token))
    log_test("List issue severities returns 200", r.status_code == 200)
    severities = r.json() if r.status_code == 200 else []
    severity_id = severities[0]["id"] if severities else 1

    r = requests.get(f"{BASE}/issues/categories", headers=h(admin_token))
    log_test("List issue categories returns 200", r.status_code == 200)
    categories = r.json() if r.status_code == 200 else []
    category_id = categories[0]["id"] if categories else None

    r = requests.get(f"{BASE}/issues/modules", headers=h(admin_token))
    log_test("List issue modules returns 200", r.status_code == 200)
    modules = r.json() if r.status_code == 200 else []
    module_id = modules[0]["id"] if modules else None

    # Create issue
    dev_id = ids.get("developer_id")
    if ids.get("project_id"):
        issue_data = {
            "title": "AutoTest Issue: Login button not responding",
            "description": "When clicking the login button on the main page, nothing happens. The form does not submit.",
            "issue_type": "Defect",
            "project_id": ids["project_id"],
            "priority_id": priority_id,
            "severity_id": severity_id,
            "status_id": status_id,
            "category_id": category_id,
            "module_id": module_id,
            "assigned_to": dev_id,
            "environment": "Production",
            "browser": "Chrome 120",
            "operating_system": "Windows 11",
            "reproduction_steps": "1. Open login page\n2. Enter credentials\n3. Click Login button",
            "expected_behavior": "User should be logged in",
            "actual_behavior": "Nothing happens",
        }
        r = requests.post(f"{BASE}/issues", json=issue_data, headers=h(admin_token))
        log_test("Create issue returns 201", r.status_code == 201, f"status={r.status_code}, body={r.text[:300]}")
        if r.status_code == 201:
            resp = r.json()
            ids["issue_id"] = resp.get("issue", {}).get("id") or resp.get("id")
            log_test("Issue ID assigned", ids["issue_id"] is not None)
            log_test("Response includes similar_issues", "similar_issues" in resp)

    # List issues
    r = requests.get(f"{BASE}/issues", headers=h(admin_token))
    log_test("List issues returns 200", r.status_code == 200)
    if r.status_code == 200:
        log_test("Issues list non-empty", len(r.json()) > 0)

    # Get issue
    if ids.get("issue_id"):
        r = requests.get(f"{BASE}/issues/{ids['issue_id']}", headers=h(admin_token))
        log_test("Get issue detail returns 200", r.status_code == 200)
        if r.status_code == 200:
            log_test("Issue has issue_key", bool(r.json().get("issue_key")))

    # Update issue
    if ids.get("issue_id") and ids.get("project_id"):
        upd = {**issue_data, "description": "Updated: Login button is completely unresponsive."}
        r = requests.put(f"{BASE}/issues/{ids['issue_id']}", json=upd, headers=h(admin_token))
        log_test("Update issue returns 200", r.status_code == 200, f"status={r.status_code}")

    # Status update
    if ids.get("issue_id") and len(statuses) > 1:
        in_prog = next((s for s in statuses if s["name"] == "In Progress"), statuses[1])
        r = requests.patch(
            f"{BASE}/issues/{ids['issue_id']}/status",
            json={"status_id": in_prog["id"], "comment": "Moving to In Progress"},
            headers=h(admin_token),
        )
        log_test("Update issue status returns 200", r.status_code == 200, f"status={r.status_code}")

    # Assign developer
    if ids.get("issue_id") and dev_id:
        r = requests.patch(
            f"{BASE}/issues/{ids['issue_id']}/assign",
            json={"assigned_to": dev_id},
            headers=h(admin_token),
        )
        log_test("Assign developer returns 200", r.status_code == 200, f"status={r.status_code}")

    # Assign QA
    qa_id = ids.get("qa_id")
    if ids.get("issue_id") and qa_id:
        r = requests.patch(
            f"{BASE}/issues/{ids['issue_id']}/assign-qa",
            json={"assigned_qa_id": qa_id},
            headers=h(admin_token),
        )
        log_test("Assign QA returns 200", r.status_code == 200, f"status={r.status_code}")

    # Add comment
    if ids.get("issue_id"):
        r = requests.post(
            f"{BASE}/issues/{ids['issue_id']}/comments",
            json={"content": "AutoTest comment: Investigating the root cause."},
            headers=h(admin_token),
        )
        log_test("Create comment returns 201", r.status_code == 201, f"status={r.status_code}")

    # List comments
    if ids.get("issue_id"):
        r = requests.get(f"{BASE}/issues/{ids['issue_id']}/comments", headers=h(admin_token))
        log_test("List comments returns 200", r.status_code == 200)
        if r.status_code == 200:
            log_test("Comments list non-empty", len(r.json()) > 0)

    # Issue history
    if ids.get("issue_id"):
        r = requests.get(f"{BASE}/issues/{ids['issue_id']}/history", headers=h(admin_token))
        log_test("Issue history returns 200", r.status_code == 200)

    # Similar issues
    if ids.get("issue_id"):
        r = requests.get(f"{BASE}/issues/{ids['issue_id']}/similar", headers=h(admin_token))
        log_test("Similar issues returns 200", r.status_code == 200)

    # Attachments list
    if ids.get("issue_id"):
        r = requests.get(f"{BASE}/issues/{ids['issue_id']}/attachments", headers=h(admin_token))
        log_test("List attachments returns 200", r.status_code == 200)

    # Filter by type
    r = requests.get(f"{BASE}/issues?issue_type=Defect", headers=h(admin_token))
    log_test("Filter by issue type returns 200", r.status_code == 200)

    # ============================================================
    # 8. SPRINTS
    # ============================================================
    print("\n>> 8. SPRINTS")

    r = requests.get(f"{BASE}/sprints/statuses", headers=h(admin_token))
    log_test("Sprint statuses returns 200", r.status_code == 200)
    sprint_statuses = r.json() if r.status_code == 200 else []
    planned_id = next((s["id"] for s in sprint_statuses if s["name"] == "Planned"), sprint_statuses[0]["id"] if sprint_statuses else 1)

    if ids.get("project_id"):
        sprint_data = {
            "name": "AutoTest Sprint 1",
            "goal": "Complete first round of testing",
            "status_id": planned_id,
            "start_date": "2026-09-20",
            "end_date": "2026-10-04",
            "project_id": ids["project_id"],
        }
        r = requests.post(f"{BASE}/sprints", json=sprint_data, headers=h(admin_token))
        log_test("Create sprint returns 201", r.status_code == 201, f"status={r.status_code}, body={r.text[:200]}")
        if r.status_code == 201:
            ids["sprint_id"] = r.json().get("id")

    r = requests.get(f"{BASE}/sprints", headers=h(admin_token))
    log_test("List sprints returns 200", r.status_code == 200)

    if ids.get("sprint_id"):
        r = requests.get(f"{BASE}/sprints/{ids['sprint_id']}", headers=h(admin_token))
        log_test("Get sprint detail returns 200", r.status_code == 200)

        r = requests.put(
            f"{BASE}/sprints/{ids['sprint_id']}",
            json={"name": "AutoTest Sprint 1 (Updated)", "goal": "Updated goal"},
            headers=h(admin_token),
        )
        log_test("Update sprint returns 200", r.status_code == 200)

    # Assign/remove issue to sprint
    if ids.get("sprint_id") and ids.get("issue_id"):
        r = requests.put(f"{BASE}/sprints/{ids['sprint_id']}/issues/{ids['issue_id']}", headers=h(admin_token))
        log_test("Assign issue to sprint returns 200", r.status_code == 200)

        r = requests.delete(f"{BASE}/sprints/{ids['sprint_id']}/issues/{ids['issue_id']}", headers=h(admin_token))
        log_test("Remove issue from sprint returns 200", r.status_code == 200)

    # ============================================================
    # 9. TEAMS
    # ============================================================
    print("\n>> 9. TEAMS")

    member_ids = [ids["developer_id"]] if ids.get("developer_id") else []
    team_data = {
        "name": "AutoTest Team",
        "description": "Automated test team",
        "team_leader_id": tl_id,
        "project_manager_id": pm_id,
        "member_ids": member_ids,
    }
    r = requests.post(f"{BASE}/teams", json=team_data, headers=h(admin_token))
    log_test("Create team returns 201", r.status_code == 201, f"status={r.status_code}, body={r.text[:300]}")
    if r.status_code == 201:
        ids["team_id"] = r.json().get("id")

    r = requests.get(f"{BASE}/teams", headers=h(admin_token))
    log_test("List teams returns 200", r.status_code == 200)

    if ids.get("team_id"):
        r = requests.get(f"{BASE}/teams/{ids['team_id']}", headers=h(admin_token))
        log_test("Get team detail returns 200", r.status_code == 200)

        r = requests.put(
            f"{BASE}/teams/{ids['team_id']}",
            json={"name": "AutoTest Team (Updated)", "description": "Updated"},
            headers=h(admin_token),
        )
        log_test("Update team returns 200", r.status_code == 200)

    r = requests.get(f"{BASE}/teams/meta/available-leaders", headers=h(admin_token))
    log_test("Available leaders returns 200", r.status_code == 200)

    r = requests.get(f"{BASE}/teams/meta/available-members", headers=h(admin_token))
    log_test("Available members returns 200", r.status_code == 200)

    r = requests.get(f"{BASE}/teams/meta/stats", headers=h(admin_token))
    log_test("Team stats returns 200", r.status_code == 200)

    # ============================================================
    # 10. DASHBOARD STATS (all roles)
    # ============================================================
    print("\n>> 10. DASHBOARD STATISTICS")

    r = requests.get(f"{BASE}/dashboard/statistics", headers=h(admin_token))
    log_test("Dashboard statistics returns 200", r.status_code == 200)
    if r.status_code == 200:
        log_test("Dashboard has total_projects", "total_projects" in r.json())
        log_test("Dashboard has total_reported_issues", "total_reported_issues" in r.json())

    r = requests.get(f"{BASE}/dashboard/admin-stats", headers=h(admin_token))
    log_test("Admin dashboard returns 200", r.status_code == 200)

    # Role-specific dashboards
    role_logins = [
        ("pm", TEST_EMAILS["pm"], "PMPass@123", "pm-stats"),
        ("tl", TEST_EMAILS["tl"], "TLPass@123", "tl-stats"),
        ("dev", TEST_EMAILS["dev"], "DevPass@123", "dev-stats"),
        ("qa", TEST_EMAILS["qa"], "QAPass@123", "qa-stats"),
        ("reporter", TEST_EMAILS["reporter"], "RepPass@123", "reporter-stats"),
    ]
    for role_key, email, password, endpoint in role_logins:
        r2 = requests.post(f"{BASE}/auth/login", json={"email": email, "password": password})
        if r2.status_code == 200:
            tok = r2.json().get("access_token")
            r = requests.get(f"{BASE}/dashboard/{endpoint}", headers=h(tok))
            log_test(f"{role_key.upper()} dashboard {endpoint} returns 200", r.status_code == 200, f"status={r.status_code}")
        else:
            log_test(f"{role_key.upper()} login for {endpoint}", False, f"status={r2.status_code}")

    # ============================================================
    # 11. ANALYTICS
    # ============================================================
    print("\n>> 11. ANALYTICS")

    r = requests.get(f"{BASE}/analytics/overview", headers=h(admin_token))
    log_test("Analytics overview returns 200", r.status_code == 200, f"status={r.status_code}")

    r = requests.get(f"{BASE}/analytics/trends", headers=h(admin_token))
    log_test("Analytics trends returns 200", r.status_code == 200, f"status={r.status_code}")

    # ============================================================
    # 12. NOTIFICATIONS
    # ============================================================
    print("\n>> 12. NOTIFICATIONS")

    r = requests.get(f"{BASE}/notifications", headers=h(admin_token))
    log_test("List notifications returns 200", r.status_code == 200)
    if r.status_code == 200:
        log_test("Notifications has items key", "items" in r.json())

    r = requests.get(f"{BASE}/notifications/unread-count", headers=h(admin_token))
    log_test("Unread count returns 200", r.status_code == 200)

    r = requests.post(f"{BASE}/notifications/mark-all-read", headers=h(admin_token))
    log_test("Mark all read returns 200", r.status_code == 200)

    r = requests.delete(f"{BASE}/notifications/read", headers=h(admin_token))
    log_test("Delete read notifications returns 200", r.status_code == 200)

    # ============================================================
    # 13. COMPANY SETTINGS & CUSTOMIZATION REQUESTS
    # ============================================================
    print("\n>> 13. COMPANY SETTINGS & CUSTOMIZATION REQUESTS")

    r = requests.get(f"{BASE}/company/profile", headers=h(admin_token))
    log_test("Get company profile returns 200", r.status_code == 200)

    r = requests.patch(f"{BASE}/company/profile", json={"phone": "+1234567890"}, headers=h(admin_token))
    log_test("Update company profile returns 200", r.status_code == 200)

    r = requests.get(f"{BASE}/company/settings", headers=h(admin_token))
    log_test("Get company settings returns 200", r.status_code == 200)

    r = requests.put(f"{BASE}/company/settings", json={"settings": {"theme": "dark"}}, headers=h(admin_token))
    log_test("Update company settings returns 200", r.status_code == 200)

    r = requests.get(f"{BASE}/company/statuses", headers=h(admin_token))
    log_test("List company statuses returns 200", r.status_code == 200)

    r = requests.post(
        f"{BASE}/company/statuses",
        json={"name": "AutoTestStatus", "category": "in_progress", "color": "#ff5722", "order_index": 10},
        headers=h(admin_token),
    )
    log_test("Create company status returns 201", r.status_code == 201, f"status={r.status_code}, body={r.text[:200]}")
    if r.status_code == 201:
        ids["company_status_id"] = r.json().get("id")

    if ids.get("company_status_id"):
        r = requests.patch(
            f"{BASE}/company/statuses/{ids['company_status_id']}",
            json={"color": "#ff9800"},
            headers=h(admin_token),
        )
        log_test("Update company status returns 200", r.status_code == 200)

    # Customization request
    cr_data = {
        "title": "AutoTest Custom Feature Request",
        "description": "We need an automated testing dashboard with real-time results display",
        "request_type": "Feature",
        "category": "Workflow",
        "requested_behavior": "A dedicated page showing test execution results in real time with pass/fail metrics",
    }
    r = requests.post(f"{BASE}/company/customization-requests", json=cr_data, headers=h(admin_token))
    log_test("Submit customization request returns 201", r.status_code == 201, f"status={r.status_code}")
    if r.status_code == 201:
        ids["cr_id"] = r.json().get("id")

    r = requests.get(f"{BASE}/company/customization-requests", headers=h(admin_token))
    log_test("List company customization requests returns 200", r.status_code == 200)

    # Super admin review
    if ids.get("cr_id"):
        r = requests.get(f"{BASE}/super-admin/customization-requests", headers=h(super_token))
        log_test("Super Admin list CRs returns 200", r.status_code == 200)

        r = requests.patch(
            f"{BASE}/super-admin/customization-requests/{ids['cr_id']}",
            json={"status": "Under Review", "super_admin_notes": "Reviewing"},
            headers=h(super_token),
        )
        log_test("Super Admin review CR returns 200", r.status_code == 200)

    # Audit logs
    r = requests.get(f"{BASE}/company/audit-logs", headers=h(admin_token))
    log_test("Company audit logs returns 200", r.status_code == 200)

    # ============================================================
    # 14. AI FEATURES
    # ============================================================
    print("\n>> 14. AI FEATURES")

    r = requests.post(
        f"{BASE}/ai/format-issue",
        json={"title": "login broken", "description": "cant login to the app it shows error"},
        headers=h(admin_token),
    )
    log_test("AI format-issue returns 200", r.status_code == 200, f"status={r.status_code}")

    if ids.get("issue_id"):
        r = requests.post(
            f"{BASE}/ai/resolution-assistance",
            json={"issue_id": ids["issue_id"]},
            headers=h(admin_token),
        )
        log_test("AI resolution-assistance returns 200", r.status_code == 200, f"status={r.status_code}")

        r = requests.post(
            f"{BASE}/ai/test-cases",
            json={"issue_id": ids["issue_id"]},
            headers=h(admin_token),
        )
        log_test("AI test-cases returns 200", r.status_code == 200, f"status={r.status_code}")

        r = requests.post(
            f"{BASE}/ai/missing-scenarios",
            json={"issue_id": ids["issue_id"], "existing_test_cases": [{"scenario": "Test login with valid credentials"}]},
            headers=h(admin_token),
        )
        log_test("AI missing-scenarios returns 200", r.status_code == 200, f"status={r.status_code}")

    # ============================================================
    # 15. COPILOT
    # ============================================================
    print("\n>> 15. COPILOT")

    r = requests.post(
        f"{BASE}/ai/copilot/chat",
        json={"message": "How many issues are open?"},
        headers=h(admin_token),
    )
    log_test("Copilot chat returns 200", r.status_code == 200, f"status={r.status_code}")

    # ============================================================
    # 16. FEATURE REQUESTS
    # ============================================================
    print("\n>> 16. FEATURE REQUESTS")

    fr_data = {
        "title": "AutoTest Feature: Dark Mode Support",
        "description": "We need a dark mode toggle for the entire application.",
        "priority_id": priority_id,
        "severity_id": severity_id,
    }
    r = requests.post(f"{BASE}/issues/feature-requests", json=fr_data, headers=h(admin_token))
    log_test("Submit feature request returns 201", r.status_code == 201, f"status={r.status_code}")
    if r.status_code == 201:
        ids["fr_id"] = r.json().get("id")

    # ============================================================
    # 17. SEARCH ENDPOINTS
    # ============================================================
    print("\n>> 17. SEARCH ENDPOINTS")

    r = requests.post(
        f"{BASE}/issues/semantic-search",
        json={"query": "login button not working", "limit": 5},
        headers=h(admin_token),
    )
    log_test("Semantic search returns 200/503", r.status_code in [200, 503], f"status={r.status_code}")

    r = requests.post(
        f"{BASE}/issues/hybrid-search",
        json={"query": "login issue", "limit": 10},
        headers=h(admin_token),
    )
    log_test("Hybrid search returns 200", r.status_code == 200, f"status={r.status_code}")

    r = requests.post(
        f"{BASE}/issues/search",
        json={"title": "Login button", "description": "not responding"},
        headers=h(admin_token),
    )
    log_test("Issue search returns 200/503", r.status_code in [200, 503], f"status={r.status_code}")

    r = requests.get(f"{BASE}/auth/users?search=Test", headers=h(admin_token))
    log_test("Users search returns 200", r.status_code == 200)

    # ============================================================
    # 18. TROUBLESHOOTING
    # ============================================================
    print("\n>> 18. TROUBLESHOOTING")

    if ids.get("issue_id"):
        r = requests.post(
            f"{BASE}/ai/troubleshooting/start",
            json={"issue_id": ids["issue_id"]},
            headers=h(admin_token),
        )
        log_test("Troubleshooting start returns 200/201/503", r.status_code in [200, 201, 503], f"status={r.status_code}")

    # ============================================================
    # 19. RBAC / AUTHORIZATION
    # ============================================================
    print("\n>> 19. RBAC / AUTHORIZATION")

    r2 = requests.post(f"{BASE}/auth/login", json={"email": TEST_EMAILS["reporter"], "password": "RepPass@123"})
    if r2.status_code == 200:
        rep_token = r2.json().get("access_token")
        r = requests.post(
            f"{BASE}/projects",
            json={"name": "Unauthorized", "key": "UNP", "status": "Active"},
            headers=h(rep_token),
        )
        log_test("Reporter cannot create project (403)", r.status_code == 403)

        r = requests.get(f"{BASE}/admin/users", headers=h(rep_token))
        log_test("Reporter cannot access admin users (403)", r.status_code == 403)

        r = requests.get(f"{BASE}/super-admin/companies", headers=h(rep_token))
        log_test("Reporter cannot access super admin (403)", r.status_code == 403)
    else:
        log_test("Reporter RBAC tests", False, "Could not login as reporter")

    # ============================================================
    # CLEANUP
    # ============================================================
    print("\n>> CLEANUP - Removing all test data")

    # Delete feature request
    if ids.get("fr_id"):
        r = requests.delete(f"{BASE}/issues/{ids['fr_id']}", headers=h(admin_token))
        log_test(f"Cleanup: delete feature request", r.status_code in [200, 204], f"status={r.status_code}")

    # Delete issue
    if ids.get("issue_id"):
        r = requests.delete(f"{BASE}/issues/{ids['issue_id']}", headers=h(admin_token))
        log_test(f"Cleanup: delete issue", r.status_code in [200, 204], f"status={r.status_code}")

    # Delete sprint
    if ids.get("sprint_id"):
        r = requests.delete(f"{BASE}/sprints/{ids['sprint_id']}", headers=h(admin_token))
        log_test(f"Cleanup: delete sprint", r.status_code in [200, 204], f"status={r.status_code}")

    # Deactivate team
    if ids.get("team_id"):
        r = requests.delete(f"{BASE}/teams/{ids['team_id']}", headers=h(admin_token))
        log_test(f"Cleanup: deactivate team", r.status_code == 200, f"status={r.status_code}")

    # Delete project
    if ids.get("project_id"):
        r = requests.delete(f"{BASE}/projects/{ids['project_id']}", headers=h(admin_token))
        log_test(f"Cleanup: delete project", r.status_code in [200, 204], f"status={r.status_code}")

    # Delete company status
    if ids.get("company_status_id"):
        r = requests.delete(f"{BASE}/company/statuses/{ids['company_status_id']}", headers=h(admin_token))
        log_test(f"Cleanup: delete company status", r.status_code == 200, f"status={r.status_code}")

    # Deactivate employees
    for role_key in ["developer", "qa", "reporter", "project_manager", "team_leader"]:
        eid = ids.get(f"{role_key}_id")
        if eid:
            r = requests.delete(f"{BASE}/admin/users/{eid}", headers=h(admin_token))
            log_test(f"Cleanup: deactivate {role_key}", r.status_code == 200, f"status={r.status_code}")

    # Delete company and purge all test records
    if ids.get("company_id") and super_token:
        r = requests.delete(f"{BASE}/super-admin/companies/{ids['company_id']}", headers=h(super_token))
        log_test("Cleanup: delete company and purge records", r.status_code == 200, f"status={r.status_code}")

    # ============================================================
    # RESULTS SUMMARY
    # ============================================================
    print("\n" + "=" * 70)
    print(f"  RESULTS: {total_passed} PASSED / {total_failed} FAILED / {total_passed + total_failed} TOTAL")
    print("=" * 70)

    if failure_details:
        print("\n  FAILED TESTS:")
        for f in failure_details:
            print(f"     - {f['name']}: {f['detail']}")

    if total_failed == 0:
        print("\n  ALL TESTS PASSED - READY FOR PRODUCTION!\n")
    else:
        print(f"\n  {total_failed} test(s) need attention.\n")

    return total_failed


if __name__ == "__main__":
    try:
        failures = run_all_tests()
        sys.exit(failures)
    except Exception as e:
        print(f"\nFATAL ERROR: {e}")
        traceback.print_exc()
        sys.exit(1)
