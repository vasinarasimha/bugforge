from typing import Any
import json
from pydantic import BaseModel, Field, field_validator


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

    @field_validator("test_data", mode="before")
    @classmethod
    def convert_test_data_to_str(cls, v: Any) -> str | None:
        if v is None:
            return None
        if isinstance(v, (dict, list)):
            return json.dumps(v)
        return str(v)

    @field_validator("steps", mode="before")
    @classmethod
    def convert_steps_to_list(cls, v: Any) -> list[str]:
        if isinstance(v, list):
            return [str(item) for item in v]
        if isinstance(v, str):
            lines = [line.strip() for line in v.split("\n") if line.strip()]
            return lines if lines else [v]
        return [str(v)] if v is not None else []


class TestCaseSummary(BaseModel):
    total_count: int = 0
    by_type: dict[str, int] = Field(default_factory=dict, description="Count of test cases per category")
    overview: str = Field(default="Generated test suite for defect verification.", description="Brief 1-2 sentence overview of the testing strategy for this defect")


class TestCaseGenerationResponse(BaseModel):
    summary: TestCaseSummary = Field(default_factory=TestCaseSummary)
    test_cases: list[TestCaseItem] = Field(default_factory=list)


class MissingScenariosRequest(BaseModel):
    issue_id: int
    existing_test_cases: list[dict | str] | None = None


class MissingScenarioItem(BaseModel):
    scenario: str = Field(description="Description of the potentially overlooked scenario")
    why_it_matters: str = Field(description="Why this scenario is important to test and what could fail")
    risk: str = Field(description="Risk assessment: High, Medium, or Low")
    suggested_test: str = Field(description="Recommended validation or test procedure to execute")
    priority: str = Field(description="Testing priority: High, Medium, or Low")


class MissingScenariosResponse(BaseModel):
    already_covered_summary: list[str] = Field(default_factory=list, description="Summary of scenarios that appear already covered")
    missing_scenarios: list[MissingScenarioItem] = Field(default_factory=list)
    disclaimer: str = "These recommendations are AI-identified coverage gaps to assist QA testing and do not guarantee complete test coverage."
