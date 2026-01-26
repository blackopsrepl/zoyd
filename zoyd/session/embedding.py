"""Embedding providers for Zoyd semantic memory.

Defines the EmbeddingProvider protocol and concrete implementations
for generating text embeddings used by vector memory operations.
"""

from __future__ import annotations

import struct
from typing import Any, Protocol, runtime_checkable

MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
MODEL_KEY = "sentence_encoder"
DIMENSION = 384
MAX_LENGTH = 128


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


class RedisAIProvider:
    """Embedding provider using RedisAI server-side ONNX inference.

    Tokenizes text locally with the ``tokenizers`` library, then sends
    token IDs and attention masks to Redis via ``AI.MODELEXECUTE`` for
    inference on the all-MiniLM-L6-v2 ONNX model.  Returns 384-dim vectors.

    Requires:
        - Redis server with RedisAI module loaded
        - Model stored via ``AI.MODELSTORE sentence_encoder ONNX CPU BLOB ...``
        - ``tokenizers`` Python package
    """

    def __init__(
        self,
        host: str = "localhost",
        port: int = 6379,
        db: int = 0,
        password: str | None = None,
        model_key: str = MODEL_KEY,
    ) -> None:
        self.host = host
        self.port = port
        self.db = db
        self.password = password
        self.model_key = model_key
        self._client: Any = None
        self._tokenizer: Any = None

    @property
    def client(self) -> Any:
        """Lazily create the Redis client."""
        if self._client is None:
            import redis

            self._client = redis.Redis(
                host=self.host,
                port=self.port,
                db=self.db,
                password=self.password,
                decode_responses=False,
            )
        return self._client

    @property
    def tokenizer(self) -> Any:
        """Lazily load the HuggingFace tokenizer."""
        if self._tokenizer is None:
            from tokenizers import Tokenizer

            self._tokenizer = Tokenizer.from_pretrained(MODEL_NAME)
            self._tokenizer.enable_truncation(max_length=MAX_LENGTH)
            self._tokenizer.enable_padding(
                length=MAX_LENGTH, pad_id=0, pad_token="[PAD]"
            )
        return self._tokenizer

    def embed(self, text: str) -> list[float]:
        """Tokenize text locally and run inference via RedisAI.

        Args:
            text: The input text to embed.

        Returns:
            A 384-dimensional embedding vector.
        """
        encoding = self.tokenizer.encode(text)
        input_ids = encoding.ids
        attention_mask = encoding.attention_mask

        ids_blob = _int64_list_to_blob(input_ids)
        mask_blob = _int64_list_to_blob(attention_mask)

        seq_len = len(input_ids)

        self.client.execute_command(
            "AI.TENSORSET", "input_ids", "INT64", 1, seq_len, "BLOB", ids_blob
        )
        self.client.execute_command(
            "AI.TENSORSET", "attention_mask", "INT64", 1, seq_len, "BLOB", mask_blob
        )

        self.client.execute_command(
            "AI.MODELEXECUTE",
            self.model_key,
            "INPUTS",
            2,
            "input_ids",
            "attention_mask",
            "OUTPUTS",
            1,
            "embeddings",
        )

        raw = self.client.execute_command("AI.TENSORGET", "embeddings", "BLOB")
        return _mean_pool(raw, attention_mask, seq_len)

    def dimension(self) -> int:
        """Return 384 (all-MiniLM-L6-v2 output dimension)."""
        return DIMENSION

    def is_available(self) -> bool:
        """Check RedisAI module and model availability."""
        try:
            self.client.execute_command("AI.INFO", self.model_key)
            _ = self.tokenizer
            return True
        except Exception:
            return False


def _int64_list_to_blob(values: list[int]) -> bytes:
    """Pack a list of ints into a little-endian INT64 blob."""
    return struct.pack(f"<{len(values)}q", *values)


def _mean_pool(
    raw: list[Any], attention_mask: list[int], seq_len: int
) -> list[float]:
    """Mean-pool token embeddings using the attention mask.

    RedisAI ``AI.TENSORGET ... BLOB`` returns ``[dtype, shape, blob]``.
    The blob contains float32 values for shape ``(1, seq_len, 384)``.
    We compute the masked mean over the sequence dimension.

    Args:
        raw: Response from ``AI.TENSORGET embeddings BLOB``.
        attention_mask: Token attention mask (1 = real, 0 = pad).
        seq_len: Number of tokens in the sequence.

    Returns:
        A list of 384 floats representing the pooled embedding.
    """
    blob: bytes = raw[2] if isinstance(raw, (list, tuple)) else raw
    floats = struct.unpack(f"<{seq_len * DIMENSION}f", blob)

    result = [0.0] * DIMENSION
    mask_sum = sum(attention_mask)
    if mask_sum == 0:
        return result

    for t in range(seq_len):
        if attention_mask[t] == 0:
            continue
        offset = t * DIMENSION
        for d in range(DIMENSION):
            result[d] += floats[offset + d]

    return [v / mask_sum for v in result]
