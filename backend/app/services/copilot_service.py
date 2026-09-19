"""
AI Copilot Service — Orchestrates tool-calling conversations with Groq.

This service is completely isolated from existing AI features (llm_service,
hf_service, troubleshooting). It handles:
1. Building system prompts with tool context
2. Sending messages to Groq with tool definitions
3. Processing tool_calls responses and dispatching to copilot_tools
4. Iterating up to MAX_TOOL_ITERATIONS before returning a final answer
"""
from __future__ import annotations

import json
import logging
from typing import Any

from groq import Groq
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.user import User
from app.services.copilot_tools import TOOL_DEFINITIONS, execute_tool

logger = logging.getLogger(__name__)

MAX_TOOL_ITERATIONS = 3

SYSTEM_PROMPT = """You are the BugForge AI Copilot — a helpful assistant embedded in the BugForge issue tracking platform.

Your capabilities:
- Search and retrieve issues/defects using natural language queries
- Look up specific issue details by ID
- Find similar defects using AI-powered semantic similarity
- Provide analytics summaries (KPIs, trends, severity distributions)
- Retrieve project and sprint information

Guidelines:
- Be concise and actionable in your responses.
- When presenting issue data, include the issue key (e.g. PROJ-123) and relevant details.
- When presenting analytics, summarize the key insights rather than dumping raw numbers.
- If a query is ambiguous, ask for clarification before invoking tools.
- You can ONLY read data. You cannot create, update, or delete anything.
- Always respect that data is scoped to the user's company — you cannot access other tenants' data.
- Format responses using markdown for readability (bold, lists, code blocks where appropriate).
- If a tool returns an error, explain it clearly to the user.
"""


class CopilotService:
    """Orchestrates AI Copilot conversations with Groq tool calling."""

    def __init__(self):
        settings = get_settings()
        self.model = settings.groq_tool_model or settings.groq_model or "qwen/qwen3.8-27b"
        self.client: Groq | None = None
        self.enabled = settings.ai_tool_calling_enabled

        try:
            if settings.groq_api_key:
                self.client = Groq(api_key=settings.groq_api_key)
            else:
                logger.warning("Groq API key not set; Copilot disabled.")
        except Exception as e:
            logger.error(f"Groq client init failed for Copilot: {e}")
            self.client = None

    def chat(
        self,
        message: str,
        db: Session,
        current_user: User,
        company_id: int | None,
        conversation_history: list[dict[str, str]] | None = None,
    ) -> dict[str, Any]:
        """
        Process a user message through the AI Copilot with tool calling.

        Returns:
            {
                "reply": str,           # The AI's final response text
                "tools_used": list,     # Names of tools that were called
                "error": str | None     # Error message if something failed
            }
        """
        if not self.enabled:
            return {
                "reply": "The AI Copilot feature is currently disabled. Please contact your administrator to enable it.",
                "tools_used": [],
                "error": None,
            }

        if not self.client:
            return {
                "reply": "AI services are not configured. Please ensure the Groq API key is set in the server configuration.",
                "tools_used": [],
                "error": "groq_client_unavailable",
            }

        # Build messages array
        messages: list[dict[str, Any]] = [{"role": "system", "content": SYSTEM_PROMPT}]

        # Add conversation history if provided (for multi-turn context)
        if conversation_history:
            for msg in conversation_history[-6:]:  # Keep last 6 messages for context
                role = msg.get("role", "user")
                content = msg.get("content", "")
                if role in ("user", "assistant") and content:
                    messages.append({"role": role, "content": content})

        # Add the current user message
        messages.append({"role": "user", "content": message})

        tools_used: list[str] = []

        try:
            for iteration in range(MAX_TOOL_ITERATIONS + 1):
                # Call Groq with tools
                response = self.client.chat.completions.create(
                    messages=messages,
                    model=self.model,
                    tools=TOOL_DEFINITIONS,
                    tool_choice="auto",
                    temperature=0.1,
                    max_tokens=4096,
                )

                choice = response.choices[0]
                assistant_message = choice.message

                # If no tool calls, return the direct response
                if not assistant_message.tool_calls:
                    return {
                        "reply": assistant_message.content or "I wasn't able to generate a response. Please try rephrasing your question.",
                        "tools_used": tools_used,
                        "error": None,
                    }

                # Process tool calls
                # Append the assistant's message (with tool_calls) to conversation
                messages.append({
                    "role": "assistant",
                    "content": assistant_message.content or "",
                    "tool_calls": [
                        {
                            "id": tc.id,
                            "type": "function",
                            "function": {
                                "name": tc.function.name,
                                "arguments": tc.function.arguments,
                            },
                        }
                        for tc in assistant_message.tool_calls
                    ],
                })

                # Execute each tool call and append results
                for tool_call in assistant_message.tool_calls:
                    tool_name = tool_call.function.name
                    tools_used.append(tool_name)

                    try:
                        arguments = json.loads(tool_call.function.arguments)
                    except json.JSONDecodeError:
                        arguments = {}

                    logger.info(
                        f"Copilot tool call: user={current_user.id}, "
                        f"tool={tool_name}, args={arguments}"
                    )

                    # Execute the tool with tenant-safe company_id
                    result = execute_tool(
                        tool_name=tool_name,
                        arguments=arguments,
                        db=db,
                        current_user=current_user,
                        company_id=company_id,
                    )

                    # Serialize result for the model
                    result_str = json.dumps(result, default=str)
                    # Truncate very large results to avoid token limits
                    if len(result_str) > 12000:
                        result_str = result_str[:12000] + '... [truncated]"}'

                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": result_str,
                    })

                # Safety: if we've hit max iterations, break
                if iteration >= MAX_TOOL_ITERATIONS:
                    logger.warning(f"Copilot hit max tool iterations ({MAX_TOOL_ITERATIONS}) for user {current_user.id}")
                    break

            # If we exhausted iterations, do one final call without tools
            response = self.client.chat.completions.create(
                messages=messages,
                model=self.model,
                temperature=0.1,
                max_tokens=4096,
            )
            return {
                "reply": response.choices[0].message.content or "I gathered some data but couldn't formulate a complete response. Please try a more specific question.",
                "tools_used": tools_used,
                "error": None,
            }

        except Exception as e:
            logger.error(f"Copilot chat error for user {current_user.id}: {e}", exc_info=True)
            return {
                "reply": "I encountered an error while processing your request. Please try again in a moment.",
                "tools_used": tools_used,
                "error": str(e),
            }


# Singleton instance
copilot_service = CopilotService()
