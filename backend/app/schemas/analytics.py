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
    avg_resolution_time_formatted: str = "No resolution-time data available"

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
    formatted: str = "No resolution-time data available"
    sample_size: int = 0

class AnalyticsOverviewResponse(BaseModel):
    kpis: KPISummary
    severity_distribution: List[SeverityDistribution]
    category_distribution: List[CategoryDistribution]
    status_distribution: List[StatusDistribution]
    developer_workload: List[DeveloperWorkload]
    defect_trends: List[DefectTrendPoint]
    resolution_metrics: ResolutionTimeMetrics
    project_id: Optional[int] = None
    project_name: Optional[str] = None
    time_range_days: int = 30
