import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient

from app.main import app
from app.api.dependencies.auth import get_current_user
from app.models.user import User
from app.models.role import Role

client = TestClient(app)


def make_mock_role(name="Developer", role_id=1):
    r = MagicMock(spec=Role)
    r.id = role_id
    r.name = name
    r.description = f"{name} role"
    return r


def make_mock_user(user_id=1, email="user@bugforge.com", full_name="Test User", role_name="Developer", is_active=True):
    u = MagicMock(spec=User)
    u.id = user_id
    u.email = email
    u.full_name = full_name
    u.is_active = is_active
    u.avatar_url = None
    u.job_title = None
    u.department = None
    u.mobile_country_code = None
    u.mobile_number = None
    u.address_line_1 = None
    u.address_line_2 = None
    u.city = None
    u.state = None
    u.state_code = None
    u.country = None
    u.country_code = None
    u.roles = [make_mock_role(role_name, role_id=1)]
    u.company_id = 1
    u.company = None
    u.company_name = "BugForge"
    u.created_at = None
    u.updated_at = None
    return u


@pytest.fixture
def mock_admin():
    return make_mock_user(user_id=1, email="admin@bugforge.com", full_name="Admin User", role_name="Admin")


@pytest.fixture
def mock_developer():
    return make_mock_user(user_id=2, email="developer@bugforge.com", full_name="Dev User", role_name="Developer")


class TestRegistrationRemoval:
    def test_public_registration_endpoint_unavailable(self):
        """Public self-registration endpoint /api/auth/register must be removed/unavailable."""
        response = client.post("/api/auth/register", json={
            "full_name": "Test User",
            "email": "test@example.com",
            "password": "password123",
        })
        assert response.status_code in (404, 405)


class TestAdminEmployeeManagement:
    def test_unauthenticated_cannot_access_admin_users(self):
        """Unauthenticated requests to admin users endpoints must return 401/403."""
        response = client.get("/api/admin/users")
        assert response.status_code in (401, 403)

        response = client.post("/api/admin/users", json={
            "full_name": "Test User",
            "email": "test@bugforge.com",
            "password": "password123",
            "role": "QA"
        })
        assert response.status_code in (401, 403)

    def test_non_admin_forbidden_from_admin_users(self, mock_developer):
        """Non-admin user receives 403 Forbidden on admin user endpoints."""
        app.dependency_overrides[get_current_user] = lambda: mock_developer
        try:
            response = client.get("/api/admin/users")
            assert response.status_code == 403

            response = client.post("/api/admin/users", json={
                "full_name": "Test User",
                "email": "test@bugforge.com",
                "password": "password123",
                "role": "QA"
            })
            assert response.status_code == 403
        finally:
            app.dependency_overrides.pop(get_current_user, None)

    def test_admin_create_employee_success(self, mock_admin):
        """Admin can create an employee with full profile details."""
        app.dependency_overrides[get_current_user] = lambda: mock_admin
        try:
            created_mock_user = make_mock_user(
                user_id=10,
                email="ravi@bugforge.com",
                full_name="Ravi Kumar",
                role_name="QA"
            )
            created_mock_user.job_title = "Senior QA Engineer"
            created_mock_user.department = "Quality Assurance"
            created_mock_user.mobile_country_code = "+91"
            created_mock_user.mobile_number = "9876543210"
            created_mock_user.address_line_1 = "123 Tech Park"
            created_mock_user.address_line_2 = "Whitefield"
            created_mock_user.city = "Bangalore"
            created_mock_user.state = "Karnataka"
            created_mock_user.state_code = "KA"
            created_mock_user.country = "India"
            created_mock_user.country_code = "IN"

            with patch('app.services.auth_service.AuthService.create_employee', return_value=created_mock_user):
                payload = {
                    "full_name": "Ravi Kumar",
                    "email": "ravi@bugforge.com",
                    "password": "SecurePassword123!",
                    "role": "QA",
                    "job_title": "Senior QA Engineer",
                    "department": "Quality Assurance",
                    "mobile_country_code": "+91",
                    "mobile_number": "9876543210",
                    "address_line_1": "123 Tech Park",
                    "address_line_2": "Whitefield",
                    "city": "Bangalore",
                    "state": "Karnataka",
                    "state_code": "KA",
                    "country": "India",
                    "country_code": "IN",
                }
                response = client.post("/api/admin/users", json=payload)
                assert response.status_code == 201
                data = response.json()
                assert data["id"] == 10
                assert data["full_name"] == "Ravi Kumar"
                assert data["email"] == "ravi@bugforge.com"
                assert data["role"] == "QA"
                assert data["mobile_country_code"] == "+91"
                assert data["mobile_number"] == "9876543210"
                assert data["city"] == "Bangalore"
                assert data["state"] == "Karnataka"
                assert data["country"] == "India"
        finally:
            app.dependency_overrides.pop(get_current_user, None)

    def test_admin_create_employee_invalid_role(self, mock_admin):
        """Admin creating an employee with an invalid role is rejected with 422."""
        app.dependency_overrides[get_current_user] = lambda: mock_admin
        try:
            payload = {
                "full_name": "Invalid Role User",
                "email": "invalid@bugforge.com",
                "password": "SecurePassword123!",
                "role": "SuperSupremeAdmin",  # Invalid role
            }
            response = client.post("/api/admin/users", json=payload)
            assert response.status_code == 422
        finally:
            app.dependency_overrides.pop(get_current_user, None)

    def test_admin_create_employee_invalid_phone(self, mock_admin):
        """Admin creating an employee with an invalid phone format is rejected."""
        app.dependency_overrides[get_current_user] = lambda: mock_admin
        try:
            payload = {
                "full_name": "Test User",
                "email": "phone@bugforge.com",
                "password": "SecurePassword123!",
                "role": "Developer",
                "mobile_number": "abc-invalid-phone",
            }
            response = client.post("/api/admin/users", json=payload)
            assert response.status_code == 422
        finally:
            app.dependency_overrides.pop(get_current_user, None)

    def test_admin_list_and_search_employees(self, mock_admin):
        """Admin can list and search employees with pagination."""
        app.dependency_overrides[get_current_user] = lambda: mock_admin
        try:
            u1 = make_mock_user(
                user_id=1,
                email="admin@bugforge.com",
                full_name="Admin User",
                role_name="Admin"
            )
            u1.job_title = "System Administrator"
            u1.department = "IT"
            u1.mobile_country_code = "+1"
            u1.mobile_number = "5551234567"
            u1.address_line_1 = "100 Main St"
            u1.city = "San Francisco"
            u1.state = "California"
            u1.state_code = "CA"
            u1.country = "United States"
            u1.country_code = "US"

            with patch('app.repositories.user_repository.UserRepository.list_employees', return_value=([u1], 1)):
                response = client.get("/api/admin/users?search=Admin&role=Admin&limit=10&offset=0")
                assert response.status_code == 200
                data = response.json()
                assert "data" in data
                assert data["total"] == 1
                assert len(data["data"]) == 1
                assert data["data"][0]["full_name"] == "Admin User"
                assert data["data"][0]["role"] == "Admin"
        finally:
            app.dependency_overrides.pop(get_current_user, None)

    def test_admin_deactivate_employee_success(self, mock_admin):
        """Admin can deactivate an employee."""
        app.dependency_overrides[get_current_user] = lambda: mock_admin
        try:
            deactivated_user = make_mock_user(
                user_id=5,
                email="former@bugforge.com",
                full_name="Former Employee",
                role_name="Developer",
                is_active=False
            )

            with patch('app.services.auth_service.AuthService.deactivate_user', return_value=deactivated_user):
                response = client.delete("/api/admin/users/5")
                assert response.status_code == 200
                data = response.json()
                assert "deactivated successfully" in data["message"]
                assert data["user"]["is_active"] is False
        finally:
            app.dependency_overrides.pop(get_current_user, None)


class TestUserProfileAndPermissions:
    def test_user_can_view_own_profile(self, mock_developer):
        """Authenticated user can view their own profile via GET /api/auth/me."""
        app.dependency_overrides[get_current_user] = lambda: mock_developer
        try:
            mock_developer.job_title = "Software Engineer"
            mock_developer.department = "Core Engineering"
            mock_developer.mobile_country_code = "+1"
            mock_developer.mobile_number = "5559876543"
            mock_developer.address_line_1 = "456 Market St"
            mock_developer.address_line_2 = "Suite 200"
            mock_developer.city = "Austin"
            mock_developer.state = "Texas"
            mock_developer.state_code = "TX"
            mock_developer.country = "United States"
            mock_developer.country_code = "US"

            response = client.get("/api/auth/me")
            assert response.status_code == 200
            data = response.json()
            assert data["id"] == 2
            assert data["full_name"] == "Dev User"
            assert data["email"] == "developer@bugforge.com"
            assert data["role"] == "Developer"
            assert data["city"] == "Austin"
        finally:
            app.dependency_overrides.pop(get_current_user, None)

    def test_user_can_update_allowed_personal_fields(self, mock_developer):
        """Authenticated user can update allowed non-sensitive fields via PATCH /api/auth/me."""
        app.dependency_overrides[get_current_user] = lambda: mock_developer
        try:
            updated_user = make_mock_user(
                user_id=2,
                email="developer@bugforge.com",
                full_name="Dev User Updated",
                role_name="Developer"
            )
            updated_user.job_title = "Senior Engineer"
            updated_user.department = "Platform"
            updated_user.mobile_country_code = "+91"
            updated_user.mobile_number = "9123456789"
            updated_user.address_line_1 = "789 Park Way"
            updated_user.city = "Hyderabad"
            updated_user.state = "Telangana"
            updated_user.state_code = "TG"
            updated_user.country = "India"
            updated_user.country_code = "IN"

            with patch('app.services.auth_service.AuthService.update_self_profile', return_value=updated_user):
                payload = {
                    "full_name": "Dev User Updated",
                    "job_title": "Senior Engineer",
                    "department": "Platform",
                    "mobile_country_code": "+91",
                    "mobile_number": "9123456789",
                    "address_line_1": "789 Park Way",
                    "city": "Hyderabad",
                    "state": "Telangana",
                    "state_code": "TG",
                    "country": "India",
                    "country_code": "IN",
                }
                response = client.patch("/api/auth/me", json=payload)
                assert response.status_code == 200
                data = response.json()
                assert data["full_name"] == "Dev User Updated"
                assert data["job_title"] == "Senior Engineer"
                assert data["city"] == "Hyderabad"
        finally:
            app.dependency_overrides.pop(get_current_user, None)

    def test_user_cannot_tamper_with_role_or_email_in_profile(self, mock_developer):
        """Sending forbidden sensitive fields (role, email, is_active) to PATCH /api/auth/me must be rejected with 422."""
        app.dependency_overrides[get_current_user] = lambda: mock_developer
        try:
            # Try to elevate privileges to Admin
            response = client.patch("/api/auth/me", json={
                "full_name": "Dev User",
                "role": "Admin",  # Forbidden field
            })
            assert response.status_code == 422

            # Try to change email
            response = client.patch("/api/auth/me", json={
                "email": "hacked@bugforge.com",  # Forbidden field
            })
            assert response.status_code == 422
        finally:
            app.dependency_overrides.pop(get_current_user, None)
