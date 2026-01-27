"""Temporary debug test to identify VADD failure."""
import json
import math
import uuid
from datetime import datetime, timezone

import pytest
from zoyd.config import load_config


class FakeProvider:
    def embed(self, text):
        vec = [0.0] * 384
        for w in text.lower().split():
            vec[hash(w) % 384] += 1.0
        n = math.sqrt(sum(v * v for v in vec)) or 1.0
        return [v / n for v in vec]
    def dimension(self):
        return 384
    def is_available(self):
        return True


def test_vadd_direct():
    try:
        import redis
    except ImportError:
        pytest.skip("redis not installed")

    config = load_config()
    try:
        client = redis.Redis(
            host=config.redis_host,
            port=config.redis_port,
            password=config.redis_password,
            decode_responses=True,
        )
        client.ping()
    except Exception:
        pytest.skip("Redis not available")

    key = "zoyd:vectors:debug:outputs"
    provider = FakeProvider()
    vector = provider.embed("hello world test")

    element_id = f"output:debug:1:{uuid.uuid4().hex[:8]}"

    # Try different VADD formats
    formats = [
        ("FP32 with VALUES", ["VADD", key, "FP32", element_id, "VALUES", len(vector), *vector]),
        ("without FP32", ["VADD", key, element_id, "VALUES", len(vector), *vector]),
        ("REDUCE 384 FP32", ["VADD", key, element_id, "REDUCE", 384, "FP32", *vector]),
        ("FP32 splat (original)", ["VADD", key, "FP32", element_id, *vector]),
    ]

    for label, args in formats:
        try:
            result = client.execute_command(*args)
            print(f"\n{label}: SUCCESS -> {result}")
            # Clean up before next test
            try:
                client.execute_command("VREM", key, element_id)
            except Exception:
                pass
        except Exception as e:
            print(f"\n{label}: FAILED -> {type(e).__name__}: {e}")

    # Also try with non-decoded client
    client2 = redis.Redis(
        host=config.redis_host,
        port=config.redis_port,
        password=config.redis_password,
        decode_responses=False,
    )
    try:
        result = client2.execute_command("VADD", key, "FP32", element_id + "_raw", *vector)
        print(f"\nFP32 with decode_responses=False: SUCCESS -> {result}")
    except Exception as e:
        print(f"\nFP32 with decode_responses=False: FAILED -> {type(e).__name__}: {e}")

    # Cleanup
    try:
        client.delete(key)
    except Exception:
        pass
