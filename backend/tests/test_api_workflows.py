import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient

from app.main import app
from app.api.dependencies.auth import get_current_user
from app.models.user import User, UserRole
from app.models.project import Project
from app.models.issue import Issue, IssueStatus, IssuePriority, IssueSeverity

client = TestClient(app)

@pytest.fixture
def mock_admin():
    u = MagicMock(spec=User)
    u.id = 1
    u.email = "admin@bugforge.com"
    u.full_name = "Admin User"
    r = MagicMock(spec=UserRole)
    r.name = "Admin"
    u.roles = [r]
    return u

@pytest.fixture
def mock_developer():
    u = MagicMock(spec=User)
    u.id = 3
    u.email = "dev@bugforge.com"
    u.full_name = "Dev User"
    r = MagicMock(spec=UserRole)
    r.name = "Developer"
    u.roles = [r]
    return u

class TestAnalyticsAPIEndpoints:

    def test_analytics_overview_unauthenticated(self):
        """Unauthenticated requests to analytics overview must return 401/403."""
        response = client.get("/api/analytics/overview")
        assert response.status_code in (401, 403)

    def test_analytics_overview_authenticated(self, mock_admin):
        """Authenticated admin can query /api/analytics/overview."""
        app.dependency_overrides[get_current_user] = lambda: mock_admin

        try:
            with patch('app.services.analytics_service.AnalyticsService.get_overview') as mock_get_overview:
                from app.schemas.analytics import (
                    AnalyticsOverviewResponse, KPISummary, ResolutionTimeMetrics
                )
                mock_get_overview.return_value = AnalyticsOverviewResponse(
                    kpis=KPISummary(
                        total_defects=10,
                        open_defects=4,
                        in_progress_defects=3,
                        resolved_defects=2,
                        closed_defects=1,
                        critical_open_defects=1,
                        avg_resolution_time_hours=18.5,
                        avg_resolution_time_formatted="18.5 hrs"
                    ),
                    severity_distribution=[],
                    category_distribution=[],
                    status_distribution=[],
                    developer_workload=[],
                    defect_trends=[],
                    resolution_metrics=ResolutionTimeMetrics(
                        avg_hours=18.5,
                        min_hours=2.0,
                        max_hours=36.0,
                        formatted="18.5 hrs",
                        sample_size=3
                    ),
                    project_id=None,
                    project_name=None,
                    time_range_days=30
                )

                response = client.get("/api/analytics/overview?days=30")
                assert response.status_code == 200
                data = response.json()
                assert data["kpis"]["total_defects"] == 10
                assert data["kpis"]["open_defects"] == 4
                assert data["kpis"]["avg_resolution_time_formatted"] == "18.5 hrs"
                assert data["resolution_metrics"]["sample_size"] == 3
        finally:
            app.dependency_overrides.pop(get_current_user, None)

    def test_analytics_kpis_endpoint(self, mock_admin):
        """Querying /api/analytics/kpis returns KPISummary model."""
        app.dependency_overrides[get_current_user] = lambda: mock_admin

        try:
            with patch('app.services.analytics_service.AnalyticsService.get_overview') as mock_get_overview:
                from app.schemas.analytics import (
                    AnalyticsOverviewResponse, KPISummary, ResolutionTimeMetrics
                )
                mock_get_overview.return_value = AnalyticsOverviewResponse(
                    kpis=KPISummary(
                        total_defects=5,
                        open_defects=2,
                        in_progress_defects=1,
                        resolved_defects=1,
                        closed_defects=1,
                        critical_open_defects=0,
                        avg_resolution_time_hours=None,
                        avg_resolution_time_formatted="No resolution-time data available"
                    ),
                    severity_distribution=[],
                    category_distribution=[],
                    status_distribution=[],
                    developer_workload=[],
                    defect_trends=[],
                    resolution_metrics=ResolutionTimeMetrics(),
                    project_id=None,
                    project_name=None,
                    time_range_days=30
                )

                response = client.get("/api/analytics/kpis")
                assert response.status_code == 200
                data = response.json()
                assert data["total_defects"] == 5
                assert data["open_defects"] == 2
        finally:
            app.dependency_overrides.pop(get_current_user, None)


class TestHealthAndDocs:

    def test_health_check_endpoint(self):
        """Health check returns healthy status."""
        response = client.get("/api/health")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"

    def test_openapi_json_available(self):
        """OpenAPI specification is accessible."""
        response = client.get("/api/openapi.json")
        assert response.status_code == 200
        assert "paths" in response.json()
        assert "/api/analytics/overview" in response.json()["paths"]
        assert "/api/issues" in response.json()["paths"]
        assert "/api/projects" in response.json()["paths"]
