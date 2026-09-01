from pydantic import BaseModel, Field


class GenerateTestCasesRequest(BaseModel):
    issue_id: int


class TestCaseItem(BaseModel):
    test_case_id: str = Field(description="Unique identifier for the test case, e.g. TC-001")
    scenario: str = Field(description="Brief title/summary of what this test case verifies")
    test_type: str = Field(description="Type of test, e.g. Positive / Functional, Negative / Boundary, Regression, Permission")
    priority: str = Field(description="Priority of the test: Critical, High, Medium, or Low")
    preconditions: str = Field(description="Prerequisites and system state needed before executing the test")
    steps: list[str] = Field(description="Ordered list of step-by-step instructions to execute the test")
    test_data: str | None = Field(default=None, description="Sample inputs or data parameters to use")
    expected_result: str = Field(description="The precise expected behavior or outcome")


class TestCaseSummary(BaseModel):
    total_count: int
    by_type: dict[str, int] = Field(default_factory=dict, description="Count of test cases per category")
    overview: str = Field(description="Brief 1-2 sentence overview of the testing strategy for this defect")


class TestCaseGenerationResponse(BaseModel):
    summary: TestCaseSummary
    test_cases: list[TestCaseItem]


class MissingScenariosRequest(BaseModel):
    issue_id: int
    existing_test_cases: list[dict] | None = None


class MissingScenarioItem(BaseModel):
    scenario: str = Field(description="Description of the potentially overlooked scenario")
    why_it_matters: str = Field(description="Why this scenario is important to test and what could fail")
    risk: str = Field(description="Risk assessment: High, Medium, or Low")
    suggested_test: str = Field(description="Recommended validation or test procedure to execute")
    priority: str = Field(description="Testing priority: High, Medium, or Low")


class MissingScenariosResponse(BaseModel):
    already_covered_summary: list[str] = Field(default_factory=list, description="Summary of scenarios that appear already covered")
    missing_scenarios: list[MissingScenarioItem]
    disclaimer: str = "These recommendations are AI-identified coverage gaps to assist QA testing and do not guarantee complete test coverage."
