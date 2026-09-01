"""
Tests for Semantic Search and Similar-Defect Detection feature.
Covers embedding generation, similarity search, thresholds, project isolation,
authorization, and graceful error handling.
"""
import pytest
from unittest.mock import patch, MagicMock
import numpy as np


# ── 1. Embedding Generation ──

class TestEmbeddingService:
    """Test the embedding service in isolation."""

    def test_embed_text_returns_384_dim_vector(self):
        """Embedding should produce a 384-dimensional vector."""
        from app.services.embedding_service import embedding_service
        result = embedding_service.embed_text("Test defect description")
        assert result is not None
        assert len(result) == 384
        # Should be a list of floats
        assert all(isinstance(x, float) for x in result)

    def test_embed_text_empty_returns_none(self):
        """Empty text should return None."""
        from app.services.embedding_service import embedding_service
        assert embedding_service.embed_text("") is None
        assert embedding_service.embed_text("   ") is None

    def test_embed_issue_combines_fields(self):
        """embed_issue should produce an embedding from combined fields."""
        from app.services.embedding_service import embedding_service
        result = embedding_service.embed_issue(
            title="Payment crash",
            description="App crashes on payment submit",
            category="Payment",
            module="Checkout",
            issue_type="Defect",
        )
        assert result is not None
        assert len(result) == 384

    def test_embed_issue_title_only(self):
        """embed_issue should work even with only title and description."""
        from app.services.embedding_service import embedding_service
        result = embedding_service.embed_issue(
            title="Login failure",
            description="Cannot log in to the system",
        )
        assert result is not None
        assert len(result) == 384

    def test_embed_query_returns_vector(self):
        """embed_query should return a 384-dim vector for search queries."""
        from app.services.embedding_service import embedding_service
        result = embedding_service.embed_query("payment crashes during checkout")
        assert result is not None
        assert len(result) == 384

    def test_build_issue_text_deterministic(self):
        """The same inputs should produce the same text representation."""
        from app.services.embedding_service import embedding_service
        text1 = embedding_service._build_issue_text("Title", "Desc", "Cat", "Mod", "Defect")
        text2 = embedding_service._build_issue_text("Title", "Desc", "Cat", "Mod", "Defect")
        assert text1 == text2

    def test_build_issue_text_structure(self):
        """Text representation should follow the expected format."""
        from app.services.embedding_service import embedding_service
        text = embedding_service._build_issue_text(
            "Payment crash", "App crashes", "Payment", "Checkout", "Defect"
        )
        assert "Title: Payment crash" in text
        assert "Description: App crashes" in text
        assert "Category: Payment" in text
        assert "Module: Checkout" in text
        assert "Type: Defect" in text

    def test_embed_text_model_not_loaded_returns_none(self):
        """If model is None, embed_text should return None gracefully."""
        from app.services.embedding_service import EmbeddingService
        svc = EmbeddingService.__new__(EmbeddingService)
        svc.model = None
        svc.dimension = 384
        assert svc.embed_text("test") is None


# ── 2. Semantic Similarity ──

class TestSemanticSimilarity:
    """Test that semantically similar texts produce similar embeddings."""

    def test_similar_texts_have_high_similarity(self):
        """Two semantically similar defect descriptions should have high cosine similarity."""
        from app.services.embedding_service import embedding_service

        vec1 = embedding_service.embed_text("Application crashes when the user submits the payment form")
        vec2 = embedding_service.embed_text("Payment page crashes during transaction submission")
        assert vec1 is not None and vec2 is not None

        # Compute cosine similarity
        a, b = np.array(vec1), np.array(vec2)
        similarity = float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))
        assert similarity > 0.60, f"Expected similarity > 0.60 for semantically similar texts, got {similarity}"

    def test_dissimilar_texts_have_low_similarity(self):
        """Two unrelated defect descriptions should have lower similarity."""
        from app.services.embedding_service import embedding_service

        vec1 = embedding_service.embed_text("Application crashes when the user submits the payment form")
        vec2 = embedding_service.embed_text("The background color of the help page is wrong")
        assert vec1 is not None and vec2 is not None

        a, b = np.array(vec1), np.array(vec2)
        similarity = float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))
        assert similarity < 0.60, f"Expected similarity < 0.60 for dissimilar texts, got {similarity}"


# ── 3. Similarity Threshold Behavior ──

class TestSimilarityThresholds:
    """Test that threshold classification works correctly."""

    def test_duplicate_threshold(self):
        """Similarity >= 0.85 should be classified as Potential Duplicate."""
        from app.core.config import get_settings
        settings = get_settings()
        assert settings.duplicate_threshold == 0.85

    def test_similar_threshold(self):
        """Similarity >= 0.60 should be classified as Similar Defect."""
        from app.core.config import get_settings
        settings = get_settings()
        assert settings.similarity_threshold == 0.60

    def test_format_similar_results_labels(self):
        """_format_similar_results should assign correct labels based on thresholds."""
        from app.services.issue_service import IssueService
        from app.core.config import get_settings

        service = IssueService()
        settings = get_settings()

        # Create mock issues
        mock_issue_dup = MagicMock()
        mock_issue_dup.id = 1
        mock_issue_dup.issue_key = "PROJ-1"
        mock_issue_dup.title = "Duplicate"
        mock_issue_dup.description = "Test"
        mock_issue_dup.status_id = 1
        mock_issue_dup.status.name = "Open"
        mock_issue_dup.severity_id = 1
        mock_issue_dup.severity.name = "High"
        mock_issue_dup.priority_id = 1
        mock_issue_dup.priority.name = "High"
        mock_issue_dup.category = None
        mock_issue_dup.module = None
        mock_issue_dup.project_id = 1
        mock_issue_dup.project.name = "Test"

        mock_issue_sim = MagicMock()
        mock_issue_sim.id = 2
        mock_issue_sim.issue_key = "PROJ-2"
        mock_issue_sim.title = "Similar"
        mock_issue_sim.description = "Test"
        mock_issue_sim.status_id = 1
        mock_issue_sim.status.name = "Open"
        mock_issue_sim.severity_id = 1
        mock_issue_sim.severity.name = "Medium"
        mock_issue_sim.priority_id = 1
        mock_issue_sim.priority.name = "Medium"
        mock_issue_sim.category = None
        mock_issue_sim.module = None
        mock_issue_sim.project_id = 1
        mock_issue_sim.project.name = "Test"

        results = [
            (mock_issue_dup, 0.90),  # Above duplicate threshold
            (mock_issue_sim, 0.70),  # Between similar and duplicate
        ]

        formatted = service._format_similar_results(results, settings)
        assert len(formatted) == 2
        assert formatted[0]["similarity_label"] == "Potential Duplicate"
        assert formatted[1]["similarity_label"] == "Similar Defect"
        assert formatted[0]["similarity_percent"] == 90.0
        assert formatted[1]["similarity_percent"] == 70.0


# ── 4. Embedding Regeneration ──

class TestEmbeddingRegeneration:
    """Test that embeddings are regenerated when semantic fields change."""

    def test_semantic_fields_include_expected_fields(self):
        """SEMANTIC_FIELDS should include title, description, category_id, module_id, issue_type."""
        from app.services.issue_service import SEMANTIC_FIELDS
        assert "title" in SEMANTIC_FIELDS
        assert "description" in SEMANTIC_FIELDS
        assert "category_id" in SEMANTIC_FIELDS
        assert "module_id" in SEMANTIC_FIELDS
        assert "issue_type" in SEMANTIC_FIELDS

    def test_non_semantic_fields_excluded(self):
        """Non-semantic fields like status_id, priority_id should not trigger regeneration."""
        from app.services.issue_service import SEMANTIC_FIELDS
        assert "status_id" not in SEMANTIC_FIELDS
        assert "priority_id" not in SEMANTIC_FIELDS
        assert "assigned_to" not in SEMANTIC_FIELDS
        assert "sprint_id" not in SEMANTIC_FIELDS
        assert "severity_id" not in SEMANTIC_FIELDS


# ── 5. Graceful Error Handling ──

class TestGracefulErrorHandling:
    """Test that embedding/search failures don't break normal operations."""

    def test_generate_embedding_safe_handles_exception(self):
        """_generate_embedding_safe should return None on failure, not raise."""
        from app.services.issue_service import IssueService
        service = IssueService()

        with patch('app.services.issue_service.embedding_service') as mock_svc:
            mock_svc.embed_issue.side_effect = RuntimeError("Model crashed")
            result = service._generate_embedding_safe("title", "desc")
            assert result is None

    def test_find_similar_issues_handles_no_embedding(self):
        """find_similar_issues should return [] if issue has no embedding."""
        from app.services.issue_service import IssueService
        service = IssueService()

        mock_db = MagicMock()
        mock_issue = MagicMock()
        mock_issue.embedding_vector = None
        mock_issue.id = 1

        with patch.object(service, 'get', return_value=mock_issue):
            result = service.find_similar_issues(mock_db, issue_id=1)
            assert result == []

    def test_semantic_search_handles_embed_failure(self):
        """semantic_search should return [] if embedding generation fails."""
        from app.services.issue_service import IssueService
        service = IssueService()

        mock_db = MagicMock()
        with patch('app.services.issue_service.embedding_service') as mock_svc:
            mock_svc.embed_query.return_value = None
            result = service.semantic_search(mock_db, query="test query")
            assert result == []


# ── 6. Schema Validation ──

class TestSchemas:
    """Test that new schemas validate correctly."""

    def test_similar_issue_response_schema(self):
        """SimilarIssueResponse should validate valid data."""
        from app.schemas.issue import SimilarIssueResponse
        data = {
            "id": 1,
            "issue_key": "PROJ-1",
            "title": "Test",
            "description": "Test desc",
            "status_id": 1,
            "status_name": "Open",
            "severity_id": 1,
            "severity_name": "High",
            "priority_id": 1,
            "priority_name": "High",
            "project_id": 1,
            "project_name": "Project",
            "similarity_score": 0.85,
            "similarity_percent": 85.0,
            "similarity_label": "Potential Duplicate",
        }
        resp = SimilarIssueResponse(**data)
        assert resp.similarity_label == "Potential Duplicate"

    def test_semantic_search_request_schema(self):
        """SemanticSearchRequest should validate valid data."""
        from app.schemas.issue import SemanticSearchRequest
        req = SemanticSearchRequest(query="payment crashes during checkout")
        assert req.query == "payment crashes during checkout"
        assert req.project_id is None
        assert req.limit is None

    def test_semantic_search_request_min_length(self):
        """SemanticSearchRequest should reject queries shorter than 3 characters."""
        from app.schemas.issue import SemanticSearchRequest
        with pytest.raises(Exception):
            SemanticSearchRequest(query="ab")

    def test_issue_create_response_schema(self):
        """IssueCreateResponse should include both issue and similar_issues."""
        from app.schemas.issue import IssueCreateResponse
        data = {
            "issue": {
                "id": 1, "issue_key": "P-1", "title": "T", "description": "D",
                "issue_type": "Defect", "status_id": 1, "status_name": "Open",
                "priority_id": 1, "priority_name": "High", "severity_id": 1,
                "severity_name": "High", "environment": None, "browser": None,
                "operating_system": None, "reproduction_steps": None,
                "expected_behavior": None, "actual_behavior": None,
                "attachment_path": None, "sprint_id": None, "sprint_name": None,
                "project_id": 1, "project_name": "P", "reporter_id": 1,
                "reporter_name": "User", "assigned_to": None, "assignee": None,
                "created_at": "2026-01-01T00:00:00", "updated_at": "2026-01-01T00:00:00",
                "is_active": True,
            },
            "similar_issues": [],
        }
        resp = IssueCreateResponse(**data)
        assert resp.issue.id == 1
        assert resp.similar_issues == []


# ── 7. Configuration ──

class TestConfiguration:
    """Test that configuration values load correctly."""

    def test_default_thresholds(self):
        """Default thresholds should be sensible for MiniLM embeddings."""
        from app.core.config import get_settings
        settings = get_settings()
        assert 0.0 < settings.similarity_threshold < 1.0
        assert 0.0 < settings.duplicate_threshold < 1.0
        assert settings.duplicate_threshold > settings.similarity_threshold
        assert settings.similar_defects_limit > 0

    def test_thresholds_configurable(self):
        """Thresholds should be configurable via environment variables."""
        import os
        from app.core.config import Settings
        # The Settings class should accept these as env vars
        assert hasattr(Settings, 'model_fields')
        assert 'similarity_threshold' in Settings.model_fields
        assert 'duplicate_threshold' in Settings.model_fields
        assert 'similar_defects_limit' in Settings.model_fields


# ── 8. Current Defect Exclusion ──

class TestExclusionOfCurrentDefect:
    """Test that the current defect is excluded at the database/backend level."""

    def test_find_similar_issues_passes_exclude_id(self):
        """find_similar_issues must pass exclude_issue_id to repository."""
        from app.services.issue_service import IssueService
        service = IssueService()

        mock_db = MagicMock()
        mock_issue = MagicMock()
        mock_issue.id = 125
        mock_issue.project_id = 1
        mock_issue.embedding_vector = [0.1] * 384

        with patch.object(service, 'get', return_value=mock_issue), \
             patch.object(service.repository, 'find_similar', return_value=[]) as mock_find:
            service.find_similar_issues(mock_db, issue_id=125)
            mock_find.assert_called_once()
            call_kwargs = mock_find.call_args[1]
            assert call_kwargs.get("exclude_issue_id") == 125

    def test_find_similar_for_embedding_passes_exclude_id(self):
        """find_similar_for_embedding must pass exclude_issue_id to repository."""
        from app.services.issue_service import IssueService
        service = IssueService()

        mock_db = MagicMock()
        with patch.object(service.repository, 'find_similar', return_value=[]) as mock_find:
            service.find_similar_for_embedding(mock_db, embedding=[0.1] * 384, exclude_issue_id=125)
            mock_find.assert_called_once()
            call_kwargs = mock_find.call_args[1]
            assert call_kwargs.get("exclude_issue_id") == 125

    def test_search_request_schema_with_exclude_id(self):
        """SearchRequest should accept and validate optional exclude_issue_id."""
        from app.api.routes.issues import SearchRequest
        req = SearchRequest(title="Crash", description="Long description text", exclude_issue_id=125, project_id=1)
        assert req.exclude_issue_id == 125
        assert req.project_id == 1
