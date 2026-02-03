"""Standalone integration tests for Redis on database 14.

Connects directly to Redis using the redis package. Written data is
intentionally NOT cleaned up — it persists after the test run.
All keys use the ``inttest:`` prefix.
"""

import time

import pytest
import redis

from zoyd.config import load_config


PREFIX = "inttest:"


@pytest.fixture(scope="module")
def r():
    """Redis client. Skips the whole module if unreachable.
    
    Reads Redis config (host, port, password, db) from zoyd.toml via load_config().
    """
    config = load_config()
    client = redis.Redis(
        host=config.redis_host,
        port=config.redis_port,
        password=config.redis_password,
        db=config.redis_db,
        decode_responses=True,
    )
    try:
        client.ping()
    except (redis.ConnectionError, redis.TimeoutError, redis.AuthenticationError):
        pytest.skip(f"Redis not available at {config.redis_host}:{config.redis_port} db {config.redis_db}")
    return client


# ── connectivity ─────────────────────────────────────────────────────

class TestPing:
    def test_ping(self, r):
        assert r.ping() is True


# ── strings ──────────────────────────────────────────────────────────

class TestStringOps:
    def test_set_get(self, r):
        key = f"{PREFIX}string:greeting"
        r.set(key, "hello redis")
        assert r.get(key) == "hello redis"

    def test_incr(self, r):
        key = f"{PREFIX}int:counter"
        r.set(key, 0)
        r.incr(key)
        r.incr(key)
        r.incr(key)
        assert int(r.get(key)) == 3


# ── hashes ───────────────────────────────────────────────────────────

class TestHashOps:
    def test_hset_hgetall(self, r):
        key = f"{PREFIX}hash:user"
        r.hset(key, mapping={"name": "zoyd", "role": "agent", "runs": "42"})
        data = r.hgetall(key)
        assert data["name"] == "zoyd"
        assert data["role"] == "agent"
        assert data["runs"] == "42"


# ── lists ────────────────────────────────────────────────────────────

class TestListOps:
    def test_rpush_lrange(self, r):
        key = f"{PREFIX}list:colors"
        r.delete(key)  # ensure clean list before push
        r.rpush(key, "red", "green", "blue")
        items = r.lrange(key, 0, -1)
        assert items == ["red", "green", "blue"]


# ── sets ─────────────────────────────────────────────────────────────

class TestSetOps:
    def test_sadd_smembers(self, r):
        key = f"{PREFIX}set:tags"
        r.sadd(key, "python", "redis", "testing")
        members = r.smembers(key)
        assert members == {"python", "redis", "testing"}


# ── sorted sets ──────────────────────────────────────────────────────

class TestSortedSetOps:
    def test_zadd_zrange(self, r):
        key = f"{PREFIX}zset:scores"
        r.zadd(key, {"alice": 10, "bob": 30, "carol": 20})
        ordered = r.zrange(key, 0, -1)
        assert ordered == ["alice", "carol", "bob"]


# ── ttl ──────────────────────────────────────────────────────────────

class TestTTL:
    def test_key_with_ttl(self, r):
        key = f"{PREFIX}ttl:temp"
        r.set(key, "expires-soon", ex=300)
        ttl = r.ttl(key)
        assert ttl > 0


# ── exists ───────────────────────────────────────────────────────────

class TestExists:
    def test_exists(self, r):
        key = f"{PREFIX}exists:check"
        r.set(key, "present")
        assert r.exists(key) == 1
