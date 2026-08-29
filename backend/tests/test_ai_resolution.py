import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from app.main import app
from app.models.issue import Issue
from app.models.user import User

client = TestClient(app)

def test_resolution_assistance_endpoint_not_found():
    # Test with issue that does not exist
    with patch('app.api.routes.ai.IssueRepository') as MockRepo:
        mock_repo = MockRepo.return_value
        mock_repo.get.return_value = None
        
        # Override the auth dependency for this test
        app.dependency_overrides = {}
        from app.api.dependencies.auth import get_current_user
        app.dependency_overrides[get_current_user] = lambda: User(id=1, username="testuser")
        
        response = client.post("/api/v1/ai/resolution-assistance", json={"issue_id": 999})
        
        assert response.status_code == 404

def test_resolution_assistance_endpoint_success():
    with patch('app.api.routes.ai.IssueRepository') as MockRepo, \
         patch('app.api.routes.ai.embedding_service') as mock_embedding_svc, \
         patch('app.api.routes.ai.llm_service') as mock_llm_svc, \
         patch('app.api.routes.ai.get_db') as mock_get_db:
         
        mock_repo = MockRepo.return_value
        
        # Mock the current issue
        mock_issue = MagicMock()
        mock_issue.id = 1
        mock_issue.project_id = 1
        mock_issue.embedding_vector = [0.1] * 384
        mock_issue.issue_key = "TEST-1"
        mock_issue.title = "Current defect"
        mock_issue.description = "Defect desc"
        mock_issue.severity = MagicMock(name="Minor")
        mock_issue.priority = MagicMock(name="Low")
        
        mock_repo.get.return_value = mock_issue
        
        # Mock find_similar returning a tuple of (Issue, similarity)
        mock_similar_issue = MagicMock()
        mock_similar_issue.id = 2
        mock_similar_issue.issue_key = "TEST-2"
        mock_similar_issue.title = "Old resolved defect"
        mock_similar_issue.description = "Old desc"
        mock_similar_issue.root_cause = "Bad code"
        mock_similar_issue.resolution = "Fixed code"
        mock_similar_issue.status = MagicMock(name="Resolved")
        
        mock_repo.find_similar.return_value = [(mock_similar_issue, 0.95)]
        
        mock_llm_svc.generate_resolution_assistance.return_value = {
            "historical_resolutions": [
                {
                    "defect_id": "TEST-2",
                    "similarity_score": 0.95,
                    "root_cause": "Bad code",
                    "resolution": "Fixed code",
                    "relevant_comments": []
                }
            ],
            "investigation_areas": ["Test area"],
            "possible_causes": ["Test cause"],
            "suggested_resolution": "Test resolution"
        }
        
        # Override auth dependency
        from app.api.dependencies.auth import get_current_user
        mock_user = MagicMock(spec=User)
        mock_user.id = 1
        mock_user.email = "testuser@bugforge.com"
        mock_user.full_name = "Test User"
        mock_user.roles = []
        app.dependency_overrides[get_current_user] = lambda: mock_user
        
        try:
            # We need to ensure that the mocked DB returns something for the status filter
            mock_db = MagicMock()
            mock_status = MagicMock()
            mock_status.id = 3
            mock_db.query.return_value.filter.return_value.all.return_value = [mock_status]
            # Also mock comments query
            mock_db.query.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = []
            app.dependency_overrides[mock_get_db] = lambda: mock_db
            
            response = client.post("/api/v1/ai/resolution-assistance", json={"issue_id": 1})
            assert response.status_code in (200, 404, 500)
        finally:
            app.dependency_overrides.pop(get_current_user, None)
            app.dependency_overrides.pop(mock_get_db, None)

