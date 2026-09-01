"""
Hugging Face AI service for the root-cause analysis troubleshooting engine.
Uses Qwen3-Coder-Next via the Hugging Face Inference API.

This is a SEPARATE service from the existing GroqService in llm_service.py.
The existing LLM service is NOT modified.
"""

import json
import logging
from typing import Any

from huggingface_hub import InferenceClient

from app.core.config import get_settings

logger = logging.getLogger(__name__)

# ── Model configuration ──
HF_MODEL = "Qwen/Qwen3-Coder-Next"
HF_PROVIDER = "novita"

# ── System Prompt ──
TROUBLESHOOTING_SYSTEM_PROMPT = """\
You are an expert software troubleshooting and root-cause analysis engine communicating with a non-technical defect Reporter (an end user, client, or business employee).

PRIMARY OBJECTIVE:
Identify the defect's root cause using an adaptive strategy with the MINIMUM number of questions necessary (maximum 10 questions). Conclude immediately as soon as you have sufficient evidence.

CRITICAL RULES FOR COMMUNICATING WITH THE REPORTER:
1. THE REPORTER IS NON-TECHNICAL: They do NOT have access to server logs, database tables, backend APIs, source code, network developer tools, or cloud infrastructure. Never ask them to check or diagnose technical internals.
2. ASK ONLY ABOUT OBSERVABLE BEHAVIOR:
   - What visible error or warning messages appeared on the screen?
   - Exactly what button, link, or menu was clicked?
   - What did they expect to happen vs what actually happened on screen?
   - Did the screen freeze, show a continuous loading spinner, turn blank, or display an alert?
   - Did the problem happen every single time, or only intermittently?
   - Does refreshing the page, logging out and back in, or trying a different browser/device change anything?
   - Did submitted data disappear, fail to save, or display incorrect values?
3. FORBIDDEN TECHNICAL JARGON:
   - Do NOT use technical terms like: API, endpoint, HTTP status code, 404/500, database, SQL, PostgreSQL, JWT, auth token, server logs, stack trace, backend, frontend, Docker, Kubernetes, infrastructure, connection pool, cache, ORM, transaction, exception, deployment.
   - Translate all technical diagnostic hypotheses into simple user-visible observations.
4. PREFER MULTIPLE-CHOICE QUESTIONS WITH SAFE FALLBACKS:
   - Provide 3 to 5 clear, mutually exclusive options (A, B, C, D...).
   - EVERY multiple-choice question MUST include a safe option like "I don't know / Not sure", "I cannot check this", or "Other / Something else".
   - Never force the reporter to guess.
5. ASK ONLY ONE FOCUSED QUESTION AT A TIME.
6. INTERNAL REASONING VS EXTERNAL OUTPUT:
   - You may use full technical rigor internally in "reasoning" and "candidate_root_causes".
   - In "question" and "options", use only plain, customer-friendly language.
   - In "root_cause", provide a clear, professional technical explanation written in understandable terms.
   - In "recommended_fix", provide actionable engineering remediation.
   - In "next_diagnostic_step", specify what developers/support should investigate next if evidence is insufficient.
7. ADAPTIVE STOPPING:
   - If confidence in a root cause reaches the threshold (>= confidence_threshold), STOP questioning immediately and return status "confirmed".
   - Do NOT ask unnecessary questions just to reach the maximum limit.
8. OUTPUT FORMAT:
   - Return ONLY the required valid JSON object. No markdown code blocks, no explanation text outside the JSON.

/no_think"""

TROUBLESHOOTING_USER_TEMPLATE = """\
DEFECT REPORT:
Title: {title}
Description: {description}
{extra_context}

CONVERSATION HISTORY ({question_count} questions answered so far):
{conversation_history}

CURRENT CANDIDATE ROOT CAUSES:
{candidate_causes}

CONFIGURATION:
- Maximum questions allowed: {max_questions}
- Confidence threshold for confirmation: {confidence_threshold}
- Current question number: {next_question_number}
{final_question_instruction}

INSTRUCTIONS:
Analyze all available observations and answers. {action_instruction}

You MUST respond with ONLY a valid JSON object in one of these formats:

FORMAT 1 — Ask a reporter-friendly question:
{{
  "status": "question",
  "question_number": {next_question_number},
  "question": "Plain-language question about what happened on screen or what the user experienced",
  "question_type": "multiple_choice",
  "options": [
    {{"id": "A", "label": "Specific observed behavior"}},
    {{"id": "B", "label": "Alternative observed behavior"}},
    {{"id": "C", "label": "Did not notice / Nothing happened"}},
    {{"id": "D", "label": "I'm not sure / I don't know"}}
  ],
  "reasoning": "Internal technical reasoning for this diagnostic step",
  "candidate_root_causes": [
    {{"cause": "Specific technical root cause hypothesis", "confidence": 0.60}},
    {{"cause": "Alternative technical hypothesis", "confidence": 0.25}}
  ]
}}

FORMAT 2 — Root cause confirmed (confidence >= {confidence_threshold}):
{{
  "status": "confirmed",
  "question_number": {next_question_number},
  "root_cause": "Clear, professional explanation of the confirmed root cause",
  "confidence": 0.90,
  "evidence": ["Observation 1 from user answers", "Observation 2 from defect report"],
  "recommended_fix": "Specific, actionable remediation step for developers",
  "next_diagnostic_step": null
}}

FORMAT 3 — Maximum questions reached or insufficient evidence to confirm:
{{
  "status": "insufficient_evidence",
  "question_number": {next_question_number},
  "root_cause": "Most likely suspected cause based on available observations",
  "confidence": 0.55,
  "evidence": ["Key observations noted so far"],
  "recommended_fix": "Suggested initial remediation or check for developers",
  "next_diagnostic_step": "Specific log, system component, or test case to inspect next"
}}

Respond with ONLY the JSON object. No markdown code blocks. No extra text."""


def _build_extra_context(defect_draft: dict) -> str:
    """Build additional context lines from the defect draft fields."""
    lines = []
    field_map = {
        "environment": "Environment",
        "browser": "Browser",
        "operating_system": "Operating System",
        "reproduction_steps": "Steps to Reproduce",
        "expected_behavior": "Expected Behavior",
        "actual_behavior": "Actual Behavior",
    }
    for key, label in field_map.items():
        val = defect_draft.get(key)
        if val and str(val).strip():
            lines.append(f"{label}: {val}")
    return "\n".join(lines) if lines else "No additional context provided."


def _build_conversation_history(answers: list[dict]) -> str:
    """Build a formatted conversation history string from saved answers."""
    if not answers:
        return "No questions asked yet."
    parts = []
    for a in answers:
        q_text = a.get("question_text", "?")
        q_type = a.get("question_type", "multiple_choice")
        selected = a.get("selected_answer", "N/A")
        options = a.get("options")
        options_str = ""
        if options:
            options_str = " | Options: " + ", ".join(
                f'{o["id"]}: {o["label"]}' for o in options if isinstance(o, dict) and "id" in o and "label" in o
            )
        parts.append(
            f"Q{a['question_number']} [{q_type}]: {q_text}{options_str}\n"
            f"  → User answered: {selected}"
        )
    return "\n".join(parts)


def _build_candidate_causes(candidates: list[dict] | None) -> str:
    """Build candidate causes summary."""
    if not candidates:
        return "No candidates identified yet — generate initial hypotheses from defect report."
    parts = []
    for c in candidates:
        if isinstance(c, dict) and "cause" in c:
            conf = c.get("confidence", 0.0)
            parts.append(f"- {c['cause']} (confidence: {conf:.2f})")
    return "\n".join(parts) if parts else "No candidates identified yet."


class HuggingFaceService:
    """
    Service for AI-powered root-cause troubleshooting via Hugging Face Inference API.
    Follows the same singleton pattern as GroqService.
    """

    def __init__(self):
        settings = get_settings()
        self.client = None
        self.model = HF_MODEL
        self.provider = HF_PROVIDER
        try:
            if settings.hf_token:
                self.client = InferenceClient(
                    provider=self.provider,
                    api_key=settings.hf_token,
                )
                logger.info("HuggingFace InferenceClient initialized successfully.")
            else:
                logger.warning(
                    "services/hf_service.py HF_TOKEN not set; AI troubleshooting features disabled."
                )
        except Exception as e:
            logger.error(f"services/hf_service.py HF client init failed: {e}; AI troubleshooting disabled.")
            self.client = None

    @property
    def is_available(self) -> bool:
        return self.client is not None

    def generate_troubleshooting_response(
        self,
        defect_draft: dict,
        answers: list[dict],
        candidate_causes: list[dict] | None,
        next_question_number: int,
        max_questions: int,
        confidence_threshold: float,
        is_final_conclusion: bool = False,
    ) -> dict[str, Any]:
        """
        Generate the next troubleshooting step: either a question or a conclusion.

        Returns a validated dict matching the structured response schema.
        Raises ValueError if the AI response is malformed after retries.
        Raises ConnectionError if the API is unreachable.
        Raises TimeoutError if the request times out.
        """
        if not self.client:
            raise ConnectionError("Hugging Face AI service is not available. HF_TOKEN may not be configured.")

        final_instruction = ""
        if is_final_conclusion:
            final_instruction = (
                "\n⚠️ THIS IS THE FINAL STEP (Maximum questions answered). "
                "You MUST return status 'confirmed' (if confidence >= {0}) "
                "or 'insufficient_evidence' (if confidence < {0}). "
                "Do NOT return status 'question'.".format(confidence_threshold)
            )

        if is_final_conclusion:
            action_instruction = (
                "You MUST conclude now with either 'confirmed' or 'insufficient_evidence'. "
                "Do NOT ask another question."
            )
        else:
            action_instruction = (
                "If you have sufficient evidence (confidence >= {0}), return a confirmed root cause. "
                "Otherwise, ask the most discriminating, reporter-friendly question.".format(confidence_threshold)
            )

        user_message = TROUBLESHOOTING_USER_TEMPLATE.format(
            title=defect_draft.get("title", "Unknown"),
            description=defect_draft.get("description", "No description provided"),
            extra_context=_build_extra_context(defect_draft),
            conversation_history=_build_conversation_history(answers),
            candidate_causes=_build_candidate_causes(candidate_causes),
            question_count=len(answers),
            max_questions=max_questions,
            confidence_threshold=confidence_threshold,
            next_question_number=next_question_number,
            final_question_instruction=final_instruction,
            action_instruction=action_instruction,
        )

        messages = [
            {"role": "system", "content": TROUBLESHOOTING_SYSTEM_PROMPT},
            {"role": "user", "content": user_message},
        ]

        # Try up to 2 attempts (1 retry with explicit error feedback on validation failure)
        last_error = None
        for attempt in range(2):
            raw_content = None
            try:
                completion = self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    temperature=0.1,
                    max_tokens=2048,
                )
                raw_content = completion.choices[0].message.content
                if not raw_content:
                    raise ValueError("Empty response from AI model")

                # Strip markdown code blocks if present
                content = raw_content.strip()
                if content.startswith("```"):
                    lines = content.split("\n")
                    if lines[0].startswith("```"):
                        lines = lines[1:]
                    if lines and lines[-1].strip() == "```":
                        lines = lines[:-1]
                    content = "\n".join(lines).strip()

                parsed = json.loads(content)
                validated = self._validate_response(parsed, next_question_number, is_final_conclusion)
                return validated

            except json.JSONDecodeError as e:
                last_error = f"AI returned invalid JSON: {e}"
                logger.warning(f"Malformed JSON from AI (attempt {attempt + 1}): {e}")
                if attempt == 0:
                    messages.append({"role": "assistant", "content": raw_content or ""})
                    messages.append({
                        "role": "user",
                        "content": "Your response was not valid JSON. Please respond with ONLY a valid JSON object matching the required schema. No markdown code blocks, no extra text."
                    })
            except (TimeoutError, ConnectionError):
                raise
            except Exception as e:
                last_error = str(e)
                logger.warning(f"AI troubleshooting response validation failed (attempt {attempt + 1}): {e}")
                if attempt == 0:
                    messages.append({"role": "assistant", "content": raw_content or "{}"})
                    messages.append({
                        "role": "user",
                        "content": f"Your previous response had the following issue: {last_error}. Please provide a corrected response adhering strictly to the JSON schema. If concluding ('confirmed' or 'insufficient_evidence'), you MUST include the 'root_cause' field."
                    })

        raise ValueError(f"Failed to get valid AI response after retries: {last_error}")

    def _validate_response(
        self, parsed: dict, expected_question_number: int, is_final_conclusion: bool
    ) -> dict[str, Any]:
        """Validate and normalize the parsed AI response."""
        if not isinstance(parsed, dict):
            raise ValueError("AI response must be a JSON object")

        status = str(parsed.get("status", "")).strip().lower()
        if not status:
            raise ValueError("AI response missing 'status' field")

        # Map status aliases if model used variant strings
        if status in ("question", "ask_question", "follow_up", "ask"):
            status = "question"
        elif status in ("confirmed", "confirm", "root_cause_confirmed", "resolved"):
            status = "confirmed"
        elif status in ("insufficient_evidence", "insufficient", "inconclusive", "unconfirmed", "max_reached"):
            status = "insufficient_evidence"

        # If on final conclusion step and AI still returned question, convert to conclusion
        if is_final_conclusion and status == "question":
            logger.warning("AI returned 'question' on final conclusion step; converting to 'insufficient_evidence'")
            status = "insufficient_evidence"

        parsed["status"] = status

        if status == "question":
            if is_final_conclusion:
                raise ValueError("AI returned 'question' when conclusion was required")

            question = parsed.get("question") or parsed.get("question_text")
            if not question or not str(question).strip():
                raise ValueError("AI question response missing 'question'")
            parsed["question"] = str(question).strip()

            q_type = parsed.get("question_type", "multiple_choice")
            if q_type not in ("multiple_choice", "yes_no", "single_select", "multi_select", "text"):
                q_type = "multiple_choice"
            parsed["question_type"] = q_type

            # Ensure options are properly structured
            options = parsed.get("options")
            if q_type in ("multiple_choice", "single_select", "multi_select", "yes_no"):
                if not options or not isinstance(options, list) or len(options) < 2:
                    if q_type == "yes_no":
                        options = [
                            {"id": "A", "label": "Yes"},
                            {"id": "B", "label": "No"},
                            {"id": "C", "label": "I'm not sure"},
                        ]
                    else:
                        options = [
                            {"id": "A", "label": "Yes, this happened"},
                            {"id": "B", "label": "No, something else happened"},
                            {"id": "C", "label": "I'm not sure / I don't know"},
                        ]
                else:
                    validated_options = []
                    letters = ["A", "B", "C", "D", "E", "F", "G", "H"]
                    for i, opt in enumerate(options):
                        if isinstance(opt, dict):
                            opt_id = str(opt.get("id") or letters[min(i, len(letters) - 1)]).strip()
                            opt_label = str(opt.get("label") or opt.get("text") or "").strip()
                            if opt_label:
                                validated_options.append({"id": opt_id, "label": opt_label})
                        elif isinstance(opt, str) and opt.strip():
                            validated_options.append({"id": letters[min(i, len(letters) - 1)], "label": opt.strip()})
                    options = validated_options if len(validated_options) >= 2 else None
            parsed["options"] = options

            parsed["question_number"] = expected_question_number
            parsed.setdefault("reasoning", "")

            # Validate candidate root causes
            validated_causes = []
            raw_causes = parsed.get("candidate_root_causes") or parsed.get("candidate_causes") or []
            if isinstance(raw_causes, list):
                for c in raw_causes:
                    if isinstance(c, dict) and ("cause" in c or "description" in c):
                        cause_text = str(c.get("cause") or c.get("description")).strip()
                        try:
                            conf = float(c.get("confidence", 0.0))
                        except (ValueError, TypeError):
                            conf = 0.0
                        if cause_text:
                            validated_causes.append({"cause": cause_text, "confidence": conf})
            parsed["candidate_root_causes"] = validated_causes

        elif status in ("confirmed", "insufficient_evidence"):
            # Robustly extract root cause across multiple possible keys
            root_cause = (
                parsed.get("root_cause")
                or parsed.get("suspected_cause")
                or parsed.get("potential_root_cause")
                or parsed.get("probable_root_cause")
                or parsed.get("probable_cause")
                or parsed.get("cause")
                or parsed.get("most_likely_cause")
            )
            if not root_cause:
                raw_causes = parsed.get("candidate_root_causes") or parsed.get("candidate_causes") or []
                if isinstance(raw_causes, list) and len(raw_causes) > 0 and isinstance(raw_causes[0], dict):
                    root_cause = raw_causes[0].get("cause")

            if not root_cause:
                if status == "insufficient_evidence":
                    root_cause = "Undetermined based on available reporter observations. Further technical investigation required."
                else:
                    raise ValueError("AI conclusion response missing 'root_cause'")

            parsed["root_cause"] = str(root_cause).strip()
            parsed["question_number"] = expected_question_number

            try:
                parsed["confidence"] = float(parsed.get("confidence", 0.85 if status == "confirmed" else 0.50))
            except (ValueError, TypeError):
                parsed["confidence"] = 0.85 if status == "confirmed" else 0.50

            # Evidence normalization
            evidence = parsed.get("evidence") or parsed.get("evidence_summary") or []
            if isinstance(evidence, list):
                parsed["evidence"] = [str(e).strip() for e in evidence if str(e).strip()]
            elif isinstance(evidence, str) and evidence.strip():
                parsed["evidence"] = [evidence.strip()]
            else:
                parsed["evidence"] = []

            # Recommended fix normalization
            fix = parsed.get("recommended_fix") or parsed.get("fix") or parsed.get("solution")
            parsed["recommended_fix"] = (
                str(fix).strip() if fix else "Investigate reported reproduction steps and review system telemetry."
            )

            # Next diagnostic step normalization
            step = parsed.get("next_diagnostic_step") or parsed.get("next_steps")
            parsed["next_diagnostic_step"] = str(step).strip() if step else None

        else:
            raise ValueError(f"Unknown AI response status: {status}")

        return parsed


# Singleton instance
hf_service = HuggingFaceService()

