"""
Copilot Tool Definitions and Execution Layer.

Defines read-only tools that the AI Copilot can invoke to query
BugForge data through existing backend services. Every tool enforces
tenant isolation via the injected company_id — never from LLM output.
"""
from __future__ import annotations

import logging
from typing import Any

from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.models.user import User
from app.services.issue_service import IssueService
from app.services.analytics_service import AnalyticsService
from app.services.project_service import ProjectService
from app.services.sprint_service import SprintService

logger = logging.getLogger(__name__)

# ────────────────────────────────────────────────────────────
# Tool argument schemas (Pydantic validation)
# ────────────────────────────────────────────────────────────

class GetIssueArgs(BaseModel):
    issue_id: int = Field(..., description="The numeric ID of the issue to retrieve")

class SearchIssuesArgs(BaseModel):
    query: str = Field(..., description="Natural language search query or keywords")
    project_id: int | None = Field(None, description="Optional project ID to scope the search")
    limit: int = Field(10, ge=1, le=25, description="Maximum number of results (1-25)")

class FindSimilarDefectsArgs(BaseModel):
    issue_id: int = Field(..., description="The numeric ID of the issue to find similar defects for")

class GetAnalyticsSummaryArgs(BaseModel):
    project_id: int | None = Field(None, description="Optional project ID to scope analytics")
    days: int = Field(30, ge=1, le=365, description="Number of days to include (1-365)")

class GetProjectSummaryArgs(BaseModel):
    project_id: int | None = Field(None, description="Specific project ID, or omit for all projects")

class GetSprintSummaryArgs(BaseModel):
    project_id: int | None = Field(None, description="Optional project ID to filter sprints")
    sprint_id: int | None = Field(None, description="Specific sprint ID to retrieve")

# ────────────────────────────────────────────────────────────
# OpenAI-compatible tool definitions (sent to Groq)
# ────────────────────────────────────────────────────────────

TOOL_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "get_issue",
            "description": "Retrieve detailed information about a specific issue/defect by its numeric ID. Returns title, description, status, priority, severity, assignees, project, and timestamps.",
            "parameters": {
                "type": "object",
                "properties": {
                    "issue_id": {
                        "type": "integer",
                        "description": "The numeric ID of the issue to retrieve"
                    }
                },
                "required": ["issue_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_issues",
            "description": "Search for issues/defects using natural language keywords or queries. Combines keyword and semantic search for best results. Use this when the user asks about issues matching a description, keyword, or topic.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Natural language search query or keywords"
                    },
                    "project_id": {
                        "type": "integer",
                        "description": "Optional project ID to scope the search"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of results (1-25, default 10)"
                    }
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "find_similar_defects",
            "description": "Find defects similar to a given issue using AI-powered semantic similarity. Returns issues ranked by similarity score.",
            "parameters": {
                "type": "object",
                "properties": {
                    "issue_id": {
                        "type": "integer",
                        "description": "The numeric ID of the issue to find similar defects for"
                    }
                },
                "required": ["issue_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_analytics_summary",
            "description": "Get an analytics overview including KPI metrics (total issues, open count, resolution rate), severity distribution, status distribution, category breakdown, and defect trends. Use this when the user asks about project health, metrics, statistics, or trends.",
            "parameters": {
                "type": "object",
                "properties": {
                    "project_id": {
                        "type": "integer",
                        "description": "Optional project ID to scope analytics"
                    },
                    "days": {
                        "type": "integer",
                        "description": "Number of days to include in trend analysis (1-365, default 30)"
                    }
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_project_summary",
            "description": "Get summary information about one or all projects. Returns project name, description, key, status, team lead, project manager, and timestamps.",
            "parameters": {
                "type": "object",
                "properties": {
                    "project_id": {
                        "type": "integer",
                        "description": "Specific project ID, or omit for all projects"
                    }
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_sprint_summary",
            "description": "Get sprint information including name, status, start/end dates, and associated project. Can return a specific sprint or list sprints for a project.",
            "parameters": {
                "type": "object",
                "properties": {
                    "project_id": {
                        "type": "integer",
                        "description": "Optional project ID to filter sprints"
                    },
                    "sprint_id": {
                        "type": "integer",
                        "description": "Specific sprint ID to retrieve"
                    }
                },
                "required": []
            }
        }
    },
]

# ────────────────────────────────────────────────────────────
# Tool execution functions
# ────────────────────────────────────────────────────────────

_issue_service = IssueService()
_project_service = ProjectService()
_sprint_service = SprintService()
_analytics_service = AnalyticsService()


def _format_issue_brief(issue) -> dict[str, Any]:
    """Format an Issue ORM object into a concise dictionary for LLM consumption."""
    return {
        "id": issue.id,
        "issue_key": issue.issue_key,
        "title": issue.title,
        "description": (issue.description or "")[:300],
        "status": issue.status.name if getattr(issue, "status", None) else "Unknown",
        "priority": issue.priority.name if getattr(issue, "priority", None) else "Unknown",
        "severity": issue.severity.name if getattr(issue, "severity", None) else "Unknown",
        "category": issue.category.name if getattr(issue, "category", None) else None,
        "module": issue.module.name if getattr(issue, "module", None) else None,
        "project": issue.project.name if getattr(issue, "project", None) else None,
        "issue_type": issue.issue_type,
        "assigned_developer": issue.assigned_developer.full_name if getattr(issue, "assigned_developer", None) else None,
        "reporter": issue.reporter.full_name if getattr(issue, "reporter", None) else None,
        "created_at": issue.created_at.isoformat() if issue.created_at else None,
        "updated_at": issue.updated_at.isoformat() if issue.updated_at else None,
    }


def _format_issue_detail(issue) -> dict[str, Any]:
    """Format an Issue ORM object with full detail for single-issue lookup."""
    brief = _format_issue_brief(issue)
    brief["description"] = issue.description or ""
    brief["steps_to_reproduce"] = issue.reproduction_steps
    brief["expected_behavior"] = issue.expected_behavior
    brief["actual_behavior"] = issue.actual_behavior
    brief["environment"] = issue.environment
    brief["browser"] = issue.browser
    brief["root_cause"] = issue.root_cause
    brief["ai_root_cause"] = issue.ai_root_cause
    brief["resolution"] = issue.resolution
    brief["assigned_qa"] = issue.assigned_qa.full_name if getattr(issue, "assigned_qa", None) else None
    brief["team"] = issue.team.name if getattr(issue, "team", None) else None
    brief["sprint"] = issue.sprint.name if getattr(issue, "sprint", None) else None
    return brief


def _format_project(project) -> dict[str, Any]:
    """Format a Project ORM object into a dictionary."""
    return {
        "id": project.id,
        "name": project.name,
        "key": project.key,
        "description": (project.description or "")[:200],
        "is_active": project.is_active,
        "project_manager": project.project_manager.full_name if getattr(project, "project_manager", None) else None,
        "team_leader": project.team_leader.full_name if getattr(project, "team_leader", None) else None,
        "created_at": project.created_at.isoformat() if getattr(project, "created_at", None) else None,
    }


def _format_sprint(sprint) -> dict[str, Any]:
    """Format a Sprint ORM object into a dictionary."""
    return {
        "id": sprint.id,
        "name": sprint.name,
        "status": sprint.status.name if getattr(sprint, "status", None) else "Unknown",
        "project": sprint.project.name if getattr(sprint, "project", None) else None,
        "start_date": sprint.start_date.isoformat() if getattr(sprint, "start_date", None) else None,
        "end_date": sprint.end_date.isoformat() if getattr(sprint, "end_date", None) else None,
        "goal": sprint.goal if getattr(sprint, "goal", None) else None,
    }


def execute_tool(
    tool_name: str,
    arguments: dict[str, Any],
    db: Session,
    current_user: User,
    company_id: int | None,
) -> dict[str, Any]:
    """
    Execute a tool by name with validated arguments.

    Security: company_id is always injected from the authenticated user context,
    never from the LLM's tool arguments. All underlying services enforce tenant
    isolation through their existing query filters.
    """
    try:
        if tool_name == "get_issue":
            args = GetIssueArgs(**arguments)
            is_bf = _issue_service.is_bugforge_user(db, current_user)
            issue = _issue_service.get(db, args.issue_id, company_id=company_id, is_bugforge=is_bf)
            if not issue:
                return {"error": f"Issue #{args.issue_id} not found or access denied."}
            return {"result": _format_issue_detail(issue)}

        elif tool_name == "search_issues":
            args = SearchIssuesArgs(**arguments)
            results = _issue_service.hybrid_search(
                db=db,
                query=args.query,
                user=current_user,
                project_id=args.project_id,
                limit=min(args.limit, 25),
            )
            formatted = [_format_issue_brief(r) for r in results[:args.limit]]
            return {"result": formatted, "count": len(formatted)}

        elif tool_name == "find_similar_defects":
            args = FindSimilarDefectsArgs(**arguments)
            similar = _issue_service.find_similar_issues(
                db=db,
                issue_id=args.issue_id,
                company_id=company_id,
            )
            return {"result": similar[:10], "count": len(similar[:10])}

        elif tool_name == "get_analytics_summary":
            args = GetAnalyticsSummaryArgs(**arguments)
            overview = _analytics_service.get_overview(
                db=db,
                current_user=current_user,
                project_id=args.project_id,
                days=args.days,
            )
            # Convert Pydantic model to dict for JSON serialization
            return {"result": overview.model_dump() if hasattr(overview, "model_dump") else overview.dict()}

        elif tool_name == "get_project_summary":
            args = GetProjectSummaryArgs(**arguments)
            if args.project_id:
                project = _project_service.get(db, args.project_id, company_id=company_id)
                if not project:
                    return {"error": f"Project #{args.project_id} not found or access denied."}
                return {"result": _format_project(project)}
            else:
                projects = _project_service.list(db, company_id=company_id)
                formatted = [_format_project(p) for p in projects]
                return {"result": formatted, "count": len(formatted)}

        elif tool_name == "get_sprint_summary":
            args = GetSprintSummaryArgs(**arguments)
            if args.sprint_id:
                sprint = _sprint_service.get(db, args.sprint_id, company_id=company_id)
                return {"result": _format_sprint(sprint)}
            else:
                sprints = _sprint_service.list(db, project_id=args.project_id, company_id=company_id)
                formatted = [_format_sprint(s) for s in sprints]
                return {"result": formatted, "count": len(formatted)}

        else:
            return {"error": f"Unknown tool: {tool_name}"}

    except HTTPException as e:
        logger.warning(f"Tool '{tool_name}' raised HTTP {e.status_code}: {e.detail}")
        return {"error": str(e.detail)}
    except Exception as e:
        logger.error(f"Tool '{tool_name}' execution error: {e}", exc_info=True)
        return {"error": f"Tool execution failed: {str(e)}"}


# Import here to avoid circular — HTTPException used in the except block above
from fastapi import HTTPException
