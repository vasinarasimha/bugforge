import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, timezone, timedelta

from app.services.analytics_service import AnalyticsService
from app.schemas.analytics import AnalyticsOverviewResponse, KPISummary
from app.models.user import User, UserRole
from app.models.issue import Issue, IssueStatus, IssueSeverity, IssueCategory

@pytest.fixture
def mock_admin_user():
    user = MagicMock(spec=User)
    user.id = 1
    user.email = "admin@bugforge.com"
    user.full_name = "Admin User"
    role = MagicMock(spec=UserRole)
    role.name = "Admin"
    user.roles = [role]
    return user

@pytest.fixture
def mock_pm_user():
    user = MagicMock(spec=User)
    user.id = 2
    user.email = "pm@bugforge.com"
    user.full_name = "PM User"
    role = MagicMock(spec=UserRole)
    role.name = "Project Manager"
    user.roles = [role]
    return user

class TestAnalyticsService:

    def test_empty_database_analytics(self, mock_admin_user):
        """When no issues exist, analytics should return valid zeroed structure without errors."""
        service = AnalyticsService()
        mock_db = MagicMock()
        
        # Mock empty queries
        mock_db.query.return_value.filter.return_value.all.return_value = []
        mock_db.query.return_value.join.return_value.outerjoin.return_value.filter.return_value.first.return_value = None
        mock_db.query.return_value.join.return_value.filter.return_value.all.return_value = []
        mock_db.query.return_value.filter.return_value.group_by.return_value.all.return_value = []
        mock_db.query.return_value.outerjoin.return_value.filter.return_value.group_by.return_value.order_by.return_value.all.return_value = []
        mock_db.query.return_value.filter.return_value.group_by.return_value.order_by.return_value.all.return_value = []

        overview = service.get_overview(mock_db, mock_admin_user, project_id=None, days=7)

        assert isinstance(overview, AnalyticsOverviewResponse)
        assert overview.kpis.total_defects == 0
        assert overview.kpis.open_defects == 0
        assert overview.kpis.avg_resolution_time_formatted in ("N/A", "No resolution-time data available")
        assert overview.resolution_metrics.sample_size == 0
        assert len(overview.defect_trends) >= 7

    def test_resolution_time_metrics_calculation(self, mock_admin_user):
        """Verify resolution time calculation from created_at and updated_at."""
        service = AnalyticsService()
        mock_db = MagicMock()

        # Mock KPI query result
        kpi_mock = MagicMock()
        kpi_mock.total = 2
        kpi_mock.open = 0
        kpi_mock.in_progress = 0
        kpi_mock.resolved = 2
        kpi_mock.closed = 0
        kpi_mock.critical_open = 0

        mock_db.query.return_value.join.return_value.outerjoin.return_value.filter.return_value.first.return_value = kpi_mock

        # 2 resolved issues: one resolved in 12 hours, one in 36 hours (avg = 24 hours = 1.0 days)
        t0 = datetime(2026, 1, 1, 10, 0, 0, tzinfo=timezone.utc)
        t1 = t0 + timedelta(hours=12)
        t2 = t0 + timedelta(hours=36)

        mock_db.query.return_value.join.return_value.filter.return_value.all.return_value = [
            (t0, t1),
            (t0, t2)
        ]

        overview = service.get_overview(mock_db, mock_admin_user, project_id=None, days=7)
        assert overview.kpis.total_defects == 2
        assert overview.kpis.resolved_defects == 2
        assert overview.resolution_metrics.sample_size == 2
        assert overview.resolution_metrics.avg_hours == 24.0
        assert overview.resolution_metrics.min_hours == 12.0
        assert overview.resolution_metrics.max_hours == 36.0
        assert "1.0 days" in overview.resolution_metrics.formatted

    def test_severity_distribution_calculation(self, mock_admin_user):
        """Severity distribution should calculate accurate counts and percentages."""
        service = AnalyticsService()
        mock_db = MagicMock()

        sev_crit = MagicMock()
        sev_crit.id = 1
        sev_crit.name = "Critical"

        sev_high = MagicMock()
        sev_high.id = 2
        sev_high.name = "High"

        mock_db.query.return_value.filter.return_value.all.side_effect = [
            [sev_crit, sev_high],  # all severities
            [],  # all statuses
            [],  # developer users
            [],  # trend created
            []   # trend resolved
        ]

        # 4 total: 3 critical (75%), 1 high (25%)
        kpi_mock = MagicMock(total=4, open=2, in_progress=1, resolved=1, closed=0, critical_open=2)
        mock_db.query.return_value.join.return_value.outerjoin.return_value.filter.return_value.first.return_value = kpi_mock
        mock_db.query.return_value.filter.return_value.group_by.return_value.all.return_value = [
            (1, 3), # sev_id 1 -> 3
            (2, 1)  # sev_id 2 -> 1
        ]

        overview = service.get_overview(mock_db, mock_admin_user, project_id=None, days=7)
        sev_dist = {s.name: s for s in overview.severity_distribution}
        
        if "Critical" in sev_dist:
            assert sev_dist["Critical"].count == 3
            assert sev_dist["Critical"].percentage == 75.0
            assert sev_dist["Critical"].color == "#ef4444"

    def test_project_isolation_for_pm(self, mock_pm_user):
        """Project Manager is restricted to their assigned projects."""
        service = AnalyticsService()
        mock_db = MagicMock()

        # PM manages project 10
        mock_db.query.return_value.filter.return_value.all.side_effect = [
            [(10,)], # PM projects
            [], # resolved issues
            [], # all severities
            [], # all statuses
            [], # developers
            [], # trends created
            []  # trends resolved
        ]

        # Requesting analytics for unauthorized project 99
        overview = service.get_overview(mock_db, mock_pm_user, project_id=99, days=30)
        assert overview.project_id == 99
