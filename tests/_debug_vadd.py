"""Debug script to check VADD against real Redis."""
import math
import redis
from zoyd.config import load_config

config = load_config()
client = redis.Redis(
    host=config.redis_host,
    port=config.redis_port,
    password=config.redis_password,
    decode_responses=True,
)
print("ping:", client.ping())

# Test VADD directly
try:
    result = client.execute_command(
        "VADD", "zoyd:vectors:test:outputs", "FP32", "test_elem_1", *([0.1] * 384)
    )
    print("VADD result:", result)
except Exception as e:
    print("VADD error:", type(e).__name__, e)

# Test VectorMemory with monkey-patching
import zoyd.session.vectors as vmod

orig_outputs = vmod.OUTPUTS_KEY
orig_meta = vmod.META_PREFIX
vmod.OUTPUTS_KEY = "zoyd:vectors:test:outputs"
vmod.META_PREFIX = "zoyd:vectors:test:meta:"

class FakeProvider:
    def embed(self, text):
        vec = [0.0] * 384
        words = text.lower().split()
        for w in words:
            vec[hash(w) % 384] += 1.0
        n = math.sqrt(sum(v * v for v in vec)) or 1.0
        return [v / n for v in vec]
    def dimension(self):
        return 384
    def is_available(self):
        return True

from zoyd.session.vectors import VectorMemory

vm = VectorMemory(
    provider=FakeProvider(),
    host=config.redis_host,
    port=config.redis_port,
    password=config.redis_password,
)

# Temporarily remove exception handler to see real error
import json, uuid
from datetime import datetime, timezone

element_id = f"output:test-sess:1:{uuid.uuid4().hex[:8]}"
vector = vm.provider.embed("hello world test")
print("vector length:", len(vector))
print("first 5 values:", vector[:5])

# Try raw VADD
try:
    r = vm.client.execute_command("VADD", vmod.OUTPUTS_KEY, "FP32", element_id, *vector)
    print("VADD via vm.client:", r)
except Exception as e:
    print("VADD via vm.client error:", type(e).__name__, e)

# Try store_output - without exception swallowing
try:
    result = vm.store_output("test-sess", 1, "hello world", "test task", 0)
    print("store_output result:", result)
except Exception as e:
    print("store_output error:", type(e).__name__, e)

# Restore
vmod.OUTPUTS_KEY = orig_outputs
vmod.META_PREFIX = orig_meta

# Cleanup
try:
    client.delete("zoyd:vectors:test:outputs")
    cursor = 0
    while True:
        cursor, keys = client.scan(cursor=cursor, match="zoyd:vectors:test:meta:*", count=100)
        if keys:
            client.delete(*keys)
        if cursor == 0:
            break
except:
    pass
