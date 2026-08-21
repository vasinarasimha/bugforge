import os
import logging
from typing import List, Optional
import numpy as np

logger = logging.getLogger(__name__)

class EmbeddingService:
    """
    Service to generate embeddings using local all-MiniLM model.
    This avoids external API calls and uses local inference.
    Optimized for low-end devices.
    """

    def __init__(self):
        # Try to load the lightweight all-MiniLM-L3-v2 model
        try:
            from sentence_transformers import SentenceTransformer
            logger.info("Loading lightweight all-MiniLM-L3-v2 model...")
            self.model = SentenceTransformer('sentence-transformers/paraphrase-MiniLM-L3-v2')
            logger.info("all-MiniLM-L3-v2 model loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load all-MiniLM-L3-v2 model: {e}")
            self.model = None

        # all-MiniLM-L3-v2 embedding dimension (matches DB column: 384)
        self.dimension = 384

    def embed_text(self, text: str) -> Optional[List[float]]:
        """
        Generate embedding for a single text string using local all-MiniLM model.
        Returns list of floats (dimension 384) or None if failed.
        """
        if not text.strip():
            return None

        if self.model is None:
            logger.error("Embedding model not loaded")
            return None

        try:
            # Generate embedding
            embedding = self.model.encode(text, normalize_embeddings=True)

            # Ensure we have the right dimension (should be 384)
            if len(embedding) != self.dimension:
                logger.warning(f"Expected dimension {self.dimension}, got {len(embedding)}")
                # Truncate or pad if needed
                if len(embedding) > self.dimension:
                    embedding = embedding[:self.dimension]
                else:
                    # Pad with zeros
                    padded = np.zeros(self.dimension)
                    padded[:len(embedding)] = embedding
                    embedding = padded

            return embedding.tolist()

        except Exception as e:
            logger.error(f"Failed to generate embedding: {e}")
            return None

    def embed_issue(self, title: str, description: str) -> Optional[List[float]]:
        """
        Generate embedding for an issue by combining title and description.
        """
        text = f"{title}\n{description}".strip()
        return self.embed_text(text)

# Singleton instance
embedding_service = EmbeddingService()