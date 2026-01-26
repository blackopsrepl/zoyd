"""Tests for zoyd.session.embedding provider auto-selection."""

from unittest.mock import MagicMock, patch

from zoyd.session.embedding import (
    DIMENSION,
    EmbeddingProvider,
    LocalOnnxProvider,
    RedisAIProvider,
    UnavailableProvider,
    get_provider,
)


class TestUnavailableProvider:
    """Tests for the UnavailableProvider stub."""

    def test_is_available_returns_false(self):
        provider = UnavailableProvider()
        assert provider.is_available() is False

    def test_dimension_returns_384(self):
        provider = UnavailableProvider()
        assert provider.dimension() == DIMENSION

    def test_embed_raises_runtime_error(self):
        provider = UnavailableProvider()
        import pytest

        with pytest.raises(RuntimeError, match="No embedding provider is available"):
            provider.embed("test")

    def test_satisfies_protocol(self):
        provider = UnavailableProvider()
        assert isinstance(provider, EmbeddingProvider)


class TestGetProvider:
    """Tests for the get_provider auto-selection function."""

    def test_returns_redis_when_available(self):
        with patch.object(RedisAIProvider, "is_available", return_value=True):
            provider = get_provider()
            assert isinstance(provider, RedisAIProvider)

    def test_returns_local_when_redis_unavailable(self):
        with patch.object(
            RedisAIProvider, "is_available", return_value=False
        ), patch.object(LocalOnnxProvider, "is_available", return_value=True):
            provider = get_provider()
            assert isinstance(provider, LocalOnnxProvider)

    def test_returns_unavailable_when_neither_works(self):
        with patch.object(
            RedisAIProvider, "is_available", return_value=False
        ), patch.object(LocalOnnxProvider, "is_available", return_value=False):
            provider = get_provider()
            assert isinstance(provider, UnavailableProvider)
            assert provider.is_available() is False

    def test_prefers_redis_over_local(self):
        """RedisAI should be tried first even if local ONNX is also available."""
        with patch.object(
            RedisAIProvider, "is_available", return_value=True
        ), patch.object(LocalOnnxProvider, "is_available", return_value=True):
            provider = get_provider()
            assert isinstance(provider, RedisAIProvider)

    def test_passes_redis_params(self):
        with patch.object(
            RedisAIProvider, "is_available", return_value=True
        ) as mock_avail:
            provider = get_provider(
                host="myhost", port=1234, db=5, password="secret", model_key="mymodel"
            )
            assert isinstance(provider, RedisAIProvider)
            assert provider.host == "myhost"
            assert provider.port == 1234
            assert provider.db == 5
            assert provider.password == "secret"
            assert provider.model_key == "mymodel"

    def test_passes_cache_dir_to_local(self):
        with patch.object(
            RedisAIProvider, "is_available", return_value=False
        ), patch.object(LocalOnnxProvider, "is_available", return_value=True):
            provider = get_provider(cache_dir="/tmp/claude/models")
            assert isinstance(provider, LocalOnnxProvider)
            assert provider._cache_dir == "/tmp/claude/models"

    def test_does_not_check_local_if_redis_available(self):
        """If RedisAI is available, LocalOnnxProvider.is_available should not be called."""
        with patch.object(
            RedisAIProvider, "is_available", return_value=True
        ), patch.object(
            LocalOnnxProvider, "is_available", return_value=True
        ) as mock_local:
            provider = get_provider()
            mock_local.assert_not_called()

    def test_result_satisfies_protocol(self):
        """All return values satisfy the EmbeddingProvider protocol."""
        with patch.object(
            RedisAIProvider, "is_available", return_value=False
        ), patch.object(LocalOnnxProvider, "is_available", return_value=False):
            provider = get_provider()
            assert isinstance(provider, EmbeddingProvider)
