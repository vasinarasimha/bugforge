from pydantic import BaseModel
from typing import Optional, List


class KPISummary(BaseModel):
    total_defects: int
    open_defects: int
    in_progress_defects: int
    resolved_defects: int
    closed_defects: int
    critical_open_defects: int
    avg_resolution_time_hours: Optional[float] = None
    avg_resolution_time_formatted: str = "N/A"


class SeverityDistribution(BaseModel):
    name: str
    count: int
    percentage: float
    color: str


class CategoryDistribution(BaseModel):
    name: str
    count: int
    percentage: float


class StatusDistribution(BaseModel):
    name: str
    count: int
    percentage: float
    color: str


class DeveloperWorkload(BaseModel):
    developer_id: int
    developer_name: str
    email: str
    total_assigned: int
    open: int
    in_progress: int
    resolved: int
    closed: int


class DefectTrendPoint(BaseModel):
    date: str
    created_count: int
    resolved_count: int


class ResolutionTimeMetrics(BaseModel):
    avg_hours: Optional[float] = None
    min_hours: Optional[float] = None
    max_hours: Optional[float] = None
    formatted: str = "N/A"
    sample_size: int = 0


class RecentDefectItem(BaseModel):
    id: int
    issue_key: str
    title: str
    severity: str
    priority: str
    status: str
    updated_at: str


class AgingDefectItem(BaseModel):
    id: int
    issue_key: str
    title: str
    severity: str
    priority: str
    status: str
    created_at: str
    days_open: int


class DeveloperPerformanceMetrics(BaseModel):
    my_assigned_defects: int
    open_defects: int
    in_progress_defects: int
    resolved_defects: int
    closed_defects: int
    critical_assigned: int
    high_assigned: int
    resolution_rate_percentage: float
    avg_resolution_time_formatted: str
    recently_resolved: List[RecentDefectItem] = []
    aging_defects: List[AgingDefectItem] = []


class TeamPerformanceSummary(BaseModel):
    team_id: int
    team_name: str
    team_leader_name: Optional[str] = None
    project_manager_name: Optional[str] = None
    member_count: int
    total_defects: int
    open_defects: int
    resolved_defects: int
    resolution_rate_percentage: float


class ModuleDistribution(BaseModel):
    """Distribution of defects by affected module/component."""
    name: str
    count: int
    percentage: float


class SprintInsight(BaseModel):
    """Sprint-level defect metrics for sprint health tracking."""
    sprint_id: int
    sprint_name: str
    project_name: Optional[str] = None
    status: str
    total_issues: int
    open_issues: int
    resolved_issues: int
    completion_rate: float
    start_date: Optional[str] = None
    end_date: Optional[str] = None


class DuplicatePattern(BaseModel):
    """AI Suggestion: Cluster of similar/duplicate defects detected via semantic similarity."""
    cluster_label: str
    issue_count: int
    issue_keys: List[str]
    avg_similarity: float
    suggestion: str


class AnalyticsOverviewResponse(BaseModel):
    kpis: KPISummary
    severity_distribution: List[SeverityDistribution]
    category_distribution: List[CategoryDistribution]
    status_distribution: List[StatusDistribution]
    developer_workload: List[DeveloperWorkload] = []
    developer_performance: Optional[DeveloperPerformanceMetrics] = None
    defect_trends: List[DefectTrendPoint]
    resolution_metrics: ResolutionTimeMetrics
    module_distribution: List[ModuleDistribution] = []
    sprint_insights: List[SprintInsight] = []
    duplicate_patterns: List[DuplicatePattern] = []
    project_id: Optional[int] = None
    project_name: Optional[str] = None
    team_id: Optional[int] = None
    team_name: Optional[str] = None
    time_range_days: int = 30
    user_role: str = "Admin"
    scope_type: str = "organization"
    scope_title: str = "Organization Overview"
    scope_teams: List[TeamPerformanceSummary] = []
    is_empty_scope: bool = False
    empty_scope_message: Optional[str] = None

