"""
Business logic for the AI-powered root-cause analysis troubleshooting engine.

Enforces the state machine, question limits, session ownership, and
idempotency rules. The AI model is called through HuggingFaceService.
"""

import logging
import uuid
from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.issue import Issue
from app.models.troubleshooting import TroubleshootingAnswer, TroubleshootingSession
from app.models.user import User
from app.repositories.project_repository import ProjectRepository
from app.services.embedding_service import embedding_service
from app.services.hf_service import hf_service

logger = logging.getLogger(__name__)

# Valid state transitions
VALID_TRANSITIONS = {
    "started": {"questioning", "cancelled"},
    "questioning": {"questioning", "confirmed", "insufficient_evidence", "cancelled"},
    "confirmed": {"completed"},
    "insufficient_evidence": {"completed"},
    "completed": set(),
    "cancelled": set(),
}


class TroubleshootingService:
    """
    Manages the lifecycle of AI troubleshooting sessions.

    State machine:
        started → questioning → confirmed → completed
                              → insufficient_evidence → completed
                 → cancelled
    """

    def _get_session(self, db: Session, session_uuid: str) -> TroubleshootingSession:
        """Fetch session by UUID, raise 404 if not found."""
        session = (
            db.query(TroubleshootingSession)
            .filter(TroubleshootingSession.session_uuid == session_uuid)
            .first()
        )
        if not session:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Troubleshooting session not found")
        return session

    def _check_ownership(self, session: TroubleshootingSession, user: User) -> None:
        """Ensure the user owns this session."""
        if session.user_id != user.id:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Not authorized to access this session")

    def _check_status(self, session: TroubleshootingSession, allowed: set[str], action: str) -> None:
        """Ensure session is in an allowed status for the given action."""
        if session.status not in allowed:
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                f"Cannot {action}: session is in '{session.status}' status"
            )

    def start_session(self, db: Session, user: User, defect_draft: dict) -> dict:
        """
        Start a new troubleshooting session and generate the first question.

        Returns the session_id and first question.
        """
        settings = get_settings()
        session_id = str(uuid.uuid4())

        # Clean draft copy
        clean_draft = dict(defect_draft) if defect_draft else {}

        # Create the session record
        ts = TroubleshootingSession(
            session_uuid=session_id,
            user_id=user.id,
            status="started",
            defect_draft=clean_draft,
            question_count=0,
            ai_model=hf_service.model if hf_service.is_available else "unavailable",
        )
        db.add(ts)
        db.flush()

        # Call AI for the first question
        try:
            ai_response = hf_service.generate_troubleshooting_response(
                defect_draft=clean_draft,
                answers=[],
                candidate_causes=None,
                next_question_number=1,
                max_questions=settings.troubleshooting_max_questions,
                confidence_threshold=settings.root_cause_confidence_threshold,
                is_final_conclusion=False,
            )
        except Exception as e:
            db.rollback()
            logger.error(f"AI troubleshooting start failed: {e}")
            raise HTTPException(
                status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="The AI troubleshooting service is temporarily unavailable. You can retry or create the issue directly."
            )

        # Process the AI response and persist
        result = self._process_ai_response(db, ts, ai_response, settings)
        db.commit()
        return result

    def submit_answer(
        self, db: Session, user: User, session_uuid: str, question_number: int, answer: str
    ) -> dict:
        """
        Submit an answer to the current question and get the next step.
        Guarantees that failed AI calls do not mutate or advance session state.
        """
        settings = get_settings()
        ts = self._get_session(db, session_uuid)
        self._check_ownership(ts, user)
        self._check_status(ts, {"started", "questioning"}, "submit answer")

        # ── Idempotency / Duplicate Check ──
        if question_number <= ts.question_count:
            # If the session already concluded, return conclusion state idempotently
            if ts.status in ("confirmed", "insufficient_evidence"):
                return {
                    "session_id": ts.session_uuid,
                    "status": ts.status,
                    "question_number": ts.question_count,
                    "root_cause": ts.root_cause,
                    "confidence": ts.confidence,
                    "evidence": ts.evidence_summary or [],
                    "recommended_fix": ts.recommended_fix,
                    "next_diagnostic_step": ts.next_diagnostic_step,
                }
            elif ts.status == "questioning":
                # Return current pending question idempotently
                pending_q = self._get_pending_question(db, ts)
                if pending_q:
                    return {
                        "session_id": ts.session_uuid,
                        "status": "questioning",
                        "question_number": pending_q.get("question_number", ts.question_count + 1),
                        "question": pending_q.get("question", "Diagnostic Question"),
                        "question_type": pending_q.get("question_type", "multiple_choice"),
                        "options": pending_q.get("options"),
                        "candidate_root_causes": ts.candidate_causes or [],
                    }
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                f"Question {question_number} has already been answered. Current question: {ts.question_count + 1}"
            )

        # Validate question number matches expected
        expected_q = ts.question_count + 1
        if question_number != expected_q:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                f"Expected answer for question {expected_q}, got {question_number}"
            )

        # Retrieve the pending question details
        pending_q = self._get_pending_question(db, ts)
        q_text = pending_q.get("question", f"Question {question_number}")
        q_type = pending_q.get("question_type", "multiple_choice")
        q_options = pending_q.get("options")

        # Prepare the answer record in-memory (DO NOT COMMIT until AI succeeds)
        answer_record = TroubleshootingAnswer(
            session_id=ts.id,
            question_number=question_number,
            question_text=q_text,
            question_type=q_type,
            options=q_options,
            selected_answer=answer,
        )

        # Build answer history including this candidate answer
        all_answers = self._build_answer_history(db, ts, extra_answer=answer_record)

        # Determine whether this is the final conclusion step
        # After answering max_questions (e.g. 10), we MUST force conclusion
        is_final_conclusion = question_number >= settings.troubleshooting_max_questions
        next_q_num = question_number if is_final_conclusion else (question_number + 1)

        # Call AI for next step
        try:
            ai_response = hf_service.generate_troubleshooting_response(
                defect_draft=ts.defect_draft,
                answers=all_answers,
                candidate_causes=ts.candidate_causes,
                next_question_number=next_q_num,
                max_questions=settings.troubleshooting_max_questions,
                confidence_threshold=settings.root_cause_confidence_threshold,
                is_final_conclusion=is_final_conclusion,
            )
        except Exception as e:
            # Roll back so no uncommitted answer or state change persists
            db.rollback()
            logger.error(f"AI troubleshooting answer failed: {e}")
            raise HTTPException(
                status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="The AI could not process your answer right now. Please try again."
            )

        # AI succeeded: now persist the answer and update session state
        db.add(answer_record)
        ts.question_count = question_number
        result = self._process_ai_response(db, ts, ai_response, settings)
        db.commit()
        return result

    def get_session(self, db: Session, user: User, session_uuid: str) -> dict:
        """Get the current state of a troubleshooting session."""
        ts = self._get_session(db, session_uuid)
        self._check_ownership(ts, user)

        answers = (
            db.query(TroubleshootingAnswer)
            .filter(TroubleshootingAnswer.session_id == ts.id)
            .order_by(TroubleshootingAnswer.question_number)
            .all()
        )

        pending_q = self._get_pending_question(db, ts) if ts.status == "questioning" else None

        return {
            "session_id": ts.session_uuid,
            "status": ts.status,
            "question_count": ts.question_count,
            "current_question": pending_q,
            "root_cause": ts.root_cause,
            "confidence": ts.confidence,
            "evidence_summary": ts.evidence_summary,
            "recommended_fix": ts.recommended_fix,
            "next_diagnostic_step": ts.next_diagnostic_step,
            "candidate_causes": ts.candidate_causes,
            "answers": [
                {
                    "question_number": a.question_number,
                    "question_text": a.question_text,
                    "question_type": a.question_type,
                    "options": a.options,
                    "selected_answer": a.selected_answer,
                }
                for a in answers
            ],
            "ai_model": ts.ai_model,
            "created_at": ts.created_at,
            "completed_at": ts.completed_at,
        }

    def confirm_and_create(
        self, db: Session, user: User, session_uuid: str, overrides: dict | None = None
    ) -> dict:
        """
        Confirm the troubleshooting result and create the actual issue.
        """
        ts = self._get_session(db, session_uuid)
        self._check_ownership(ts, user)
        self._check_status(ts, {"confirmed", "insufficient_evidence"}, "confirm and create issue")

        # Build issue data from the defect draft + any overrides
        raw_draft = dict(ts.defect_draft) if ts.defect_draft else {}
        # Remove internal metadata keys
        raw_draft.pop("_current_question", None)

        issue_data = raw_draft
        if overrides:
            for key, val in overrides.items():
                if val is not None:
                    issue_data[key] = val

        # Set root cause from the AI session
        if ts.root_cause:
            issue_data["root_cause"] = ts.root_cause

        # Create the issue using IssueService
        from app.schemas.issue import IssueCreate
        from app.services.issue_service import IssueService

        issue_service = IssueService()

        create_payload = IssueCreate(
            title=issue_data.get("title", "Untitled"),
            description=issue_data.get("description", "No description"),
            issue_type=issue_data.get("issue_type", "Defect"),
            project_id=issue_data.get("project_id", 1),
            priority_id=issue_data.get("priority_id", 1),
            severity_id=issue_data.get("severity_id", 1),
            status_id=issue_data.get("status_id", 1),
            category_id=issue_data.get("category_id"),
            module_id=issue_data.get("module_id"),
            assigned_to=issue_data.get("assigned_to"),
            environment=issue_data.get("environment"),
            browser=issue_data.get("browser"),
            operating_system=issue_data.get("operating_system"),
            reproduction_steps=issue_data.get("reproduction_steps"),
            expected_behavior=issue_data.get("expected_behavior"),
            actual_behavior=issue_data.get("actual_behavior"),
            root_cause=issue_data.get("root_cause"),
            sprint_id=issue_data.get("sprint_id"),
        )

        created_issue = issue_service.create(db, create_payload, user)

        # Link the session to the issue
        created_issue.ai_root_cause_session_id = ts.id
        ts.status = "completed"
        ts.completed_at = datetime.now(timezone.utc)
        db.commit()
        try:
            db.refresh(created_issue)
        except Exception:
            pass


        # Find similar issues for reporting
        similar_issues = []
        try:
            if created_issue.embedding_vector is not None:
                similar_issues = issue_service.find_similar_for_embedding(
                    db,
                    embedding=list(created_issue.embedding_vector),
                    exclude_issue_id=created_issue.id,
                    project_id=created_issue.project_id,
                )
        except Exception as e:
            logger.error(f"Similar issue detection during confirm_and_create failed: {e}")

        return {
            "issue_id": created_issue.id,
            "issue_key": created_issue.issue_key,
            "session_id": ts.session_uuid,
            "root_cause": ts.root_cause,
            "confidence": ts.confidence,
            "status": "completed",
            "similar_issues": similar_issues,
        }

    def cancel_session(self, db: Session, user: User, session_uuid: str) -> None:
        """Cancel a troubleshooting session."""
        ts = self._get_session(db, session_uuid)
        self._check_ownership(ts, user)
        self._check_status(
            ts, {"started", "questioning", "confirmed", "insufficient_evidence"}, "cancel"
        )
        ts.status = "cancelled"
        ts.completed_at = datetime.now(timezone.utc)
        db.commit()

    # ── Private helpers ──

    def _process_ai_response(
        self, db: Session, ts: TroubleshootingSession, ai_response: dict, settings
    ) -> dict:
        """Process a validated AI response and update session state."""
        response_status = ai_response.get("status")

        if response_status == "question":
            ts.status = "questioning"
            ts.candidate_causes = ai_response.get("candidate_root_causes", [])

            # Persist current question into defect_draft so it survives across requests
            draft = dict(ts.defect_draft) if ts.defect_draft else {}
            draft["_current_question"] = {
                "question_number": ai_response["question_number"],
                "question": ai_response["question"],
                "question_type": ai_response["question_type"],
                "options": ai_response.get("options"),
                "candidate_root_causes": ai_response.get("candidate_root_causes", []),
            }
            ts.defect_draft = draft

            return {
                "session_id": ts.session_uuid,
                "status": "questioning",
                "question_number": ai_response["question_number"],
                "question": ai_response["question"],
                "question_type": ai_response["question_type"],
                "options": ai_response.get("options"),
                "candidate_root_causes": ai_response.get("candidate_root_causes", []),
            }

        elif response_status in ("confirmed", "insufficient_evidence"):
            ts.status = response_status
            ts.root_cause = ai_response.get("root_cause")
            ts.confidence = ai_response.get("confidence")
            ts.evidence_summary = ai_response.get("evidence", [])
            ts.recommended_fix = ai_response.get("recommended_fix")
            ts.next_diagnostic_step = ai_response.get("next_diagnostic_step")
            ts.completed_at = datetime.now(timezone.utc)

            # Clear pending question
            if ts.defect_draft and "_current_question" in ts.defect_draft:
                draft = dict(ts.defect_draft)
                draft.pop("_current_question", None)
                ts.defect_draft = draft

            return {
                "session_id": ts.session_uuid,
                "status": response_status,
                "question_number": ai_response.get("question_number", ts.question_count),
                "root_cause": ts.root_cause,
                "confidence": ts.confidence,
                "evidence": ts.evidence_summary,
                "recommended_fix": ts.recommended_fix,
                "next_diagnostic_step": ts.next_diagnostic_step,
            }

        else:
            raise ValueError(f"Unexpected AI response status: {response_status}")

    def _get_pending_question(self, db: Session, ts: TroubleshootingSession) -> dict:
        """
        Get the pending question info from persisted session metadata.
        """
        if ts.defect_draft and isinstance(ts.defect_draft, dict) and "_current_question" in ts.defect_draft:
            return ts.defect_draft["_current_question"]

        return {
            "question": f"Diagnostic Question {ts.question_count + 1}",
            "question_type": "multiple_choice",
            "options": None,
            "question_number": ts.question_count + 1,
        }

    def _build_answer_history(
        self, db: Session, ts: TroubleshootingSession, extra_answer: TroubleshootingAnswer | None = None
    ) -> list[dict]:
        """Build the complete answer history for the AI prompt."""
        answers = (
            db.query(TroubleshootingAnswer)
            .filter(TroubleshootingAnswer.session_id == ts.id)
            .order_by(TroubleshootingAnswer.question_number)
            .all()
        )
        result = []
        for a in answers:
            result.append({
                "question_number": a.question_number,
                "question_text": a.question_text,
                "question_type": a.question_type,
                "options": a.options,
                "selected_answer": a.selected_answer,
            })
        if extra_answer and extra_answer.question_number not in [a["question_number"] for a in result]:
            result.append({
                "question_number": extra_answer.question_number,
                "question_text": extra_answer.question_text,
                "question_type": extra_answer.question_type,
                "options": extra_answer.options,
                "selected_answer": extra_answer.selected_answer,
            })
        return result


# Singleton
troubleshooting_service = TroubleshootingService()

