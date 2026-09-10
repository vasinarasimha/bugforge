import logging
from typing import Optional

import numpy as np

logger = logging.getLogger(__name__)


class EmbeddingService:
    """
    Service to generate embeddings using local all-MiniLM-L6-v2 model.
    This avoids external API calls and uses local inference.
    The model is loaded once (singleton) and reused for all requests.
    """

    def __init__(self):
        self._model = None
        # all-MiniLM-L6-v2 embedding dimension
        self.dimension = 384

    @property
    def model(self):
        if self._model is None and not getattr(self, "_model_disabled", False):
            try:
                from sentence_transformers import SentenceTransformer
                logger.info("Loading all-MiniLM-L6-v2 model...")
                self._model = SentenceTransformer('all-MiniLM-L6-v2')
                logger.info("all-MiniLM-L6-v2 model loaded successfully")
            except Exception as e:
                logger.error(f"Failed to load all-MiniLM-L6-v2 model: {e}")
                self._model = None
                self._model_disabled = True
        return self._model

    @model.setter
    def model(self, value):
        self._model = value
        self._model_disabled = (value is None)

    def embed_text(self, text: str) -> Optional[list[float]]:
        """
        Generate embedding for a single text string using local all-MiniLM model.
        Returns list of floats (dimension 384) or None if failed.
        """
        if not text or not text.strip():
            return None

        if self.model is None:
            logger.error("Embedding model not loaded")
            return None

        try:
            embedding = self.model.encode(text, normalize_embeddings=True)

            if len(embedding) != self.dimension:
                logger.warning(f"Expected dimension {self.dimension}, got {len(embedding)}")
                if len(embedding) > self.dimension:
                    embedding = embedding[:self.dimension]
                else:
                    padded = np.zeros(self.dimension)
                    padded[:len(embedding)] = embedding
                    embedding = padded

            return embedding.tolist()

        except Exception as e:
            logger.error(f"Failed to generate embedding: {e}")
            return None

    def _build_issue_text(
        self,
        title: str,
        description: str,
        category: str | None = None,
        module: str | None = None,
        issue_type: str | None = None,
    ) -> str:
        """
        Build a deterministic text representation of an issue for embedding.
        Combines the most semantically meaningful fields.
        """
        parts = []
        if title and title.strip():
            parts.append(f"Title: {title.strip()}")
        if description and description.strip():
            parts.append(f"Description: {description.strip()}")
        if issue_type and issue_type.strip():
            parts.append(f"Type: {issue_type.strip()}")
        if category and category.strip():
            parts.append(f"Category: {category.strip()}")
        if module and module.strip():
            parts.append(f"Module: {module.strip()}")
        return "\n".join(parts)

    def embed_issue(
        self,
        title: str,
        description: str,
        category: str | None = None,
        module: str | None = None,
        issue_type: str | None = None,
    ) -> Optional[list[float]]:
        """
        Generate embedding for an issue by combining semantically meaningful fields.
        """
        text = self._build_issue_text(title, description, category, module, issue_type)
        return self.embed_text(text)

    def embed_query(self, query: str) -> Optional[list[float]]:
        """
        Generate embedding for a natural-language search query.
        """
        return self.embed_text(query)


# Singleton instance — loaded once and reused across all requests
embedding_service = EmbeddingService()