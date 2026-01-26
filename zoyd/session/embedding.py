"""Embedding providers for Zoyd semantic memory.

Defines the EmbeddingProvider protocol and concrete implementations
for generating text embeddings used by vector memory operations.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class EmbeddingProvider(Protocol):
    """Protocol for text embedding providers.

    Implementations convert text into fixed-dimension float vectors
    suitable for similarity search via Redis VSET commands.
    """

    def embed(self, text: str) -> list[float]:
        """Convert text into a vector embedding.

        Args:
            text: The input text to embed.

        Returns:
            A list of floats representing the embedding vector.
        """
        ...

    def dimension(self) -> int:
        """Return the dimensionality of embedding vectors.

        Returns:
            The number of dimensions in vectors produced by embed().
        """
        ...

    def is_available(self) -> bool:
        """Check whether this provider is ready to produce embeddings.

        Returns:
            True if the provider can generate embeddings, False otherwise.
        """
        ...
