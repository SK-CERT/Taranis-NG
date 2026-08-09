"""Opaque Redis authentication transaction behavior."""

from __future__ import annotations

import base64
import threading
from concurrent.futures import ThreadPoolExecutor

import pytest
from managers import auth_transaction_manager
from managers.auth_transaction_manager import AuthTransactionKind


class MemoryRedis:
    """Small thread-safe Redis stand-in implementing the operations under test."""

    def __init__(self) -> None:
        """Create an empty in-memory transaction store."""
        self.values: dict[str, bytes] = {}
        self.ttls: dict[str, int] = {}
        self.lock = threading.Lock()
        self.get_calls = 0
        self.getdel_calls = 0

    def set(self, key: str, value: str, *, ex: int, nx: bool) -> bool:
        """Store a value with Redis-compatible NX and expiry arguments."""
        with self.lock:
            if nx and key in self.values:
                return False
            self.values[key] = value.encode()
            self.ttls[key] = ex
            return True

    def get(self, key: str) -> bytes | None:
        """Read a value without consuming it."""
        with self.lock:
            self.get_calls += 1
            return self.values.get(key)

    def getdel(self, key: str) -> bytes | None:
        """Atomically read and consume a value."""
        with self.lock:
            self.getdel_calls += 1
            self.ttls.pop(key, None)
            return self.values.pop(key, None)


@pytest.fixture
def memory_redis(monkeypatch: pytest.MonkeyPatch) -> MemoryRedis:
    redis = MemoryRedis()
    monkeypatch.setattr(auth_transaction_manager, "redis_client", redis)
    return redis


def test_create_returns_256_bit_opaque_token_and_sets_ttl(memory_redis: MemoryRedis) -> None:
    token = auth_transaction_manager.create(AuthTransactionKind.OAUTH_STATE, {"provider_id": 7}, 600)

    padding = "=" * (-len(token) % 4)
    assert len(base64.urlsafe_b64decode(token + padding)) == auth_transaction_manager.TOKEN_BYTES
    assert "." not in token
    assert next(iter(memory_redis.ttls.values())) == 600


@pytest.mark.usefixtures("memory_redis")
def test_peek_is_non_destructive_and_consume_is_one_time() -> None:
    token = auth_transaction_manager.create(AuthTransactionKind.OAUTH_STATE, {"nonce": "secret"}, 60)

    assert auth_transaction_manager.peek(AuthTransactionKind.OAUTH_STATE, token) == {"nonce": "secret"}
    assert auth_transaction_manager.peek(AuthTransactionKind.OAUTH_STATE, token) == {"nonce": "secret"}
    assert auth_transaction_manager.consume(AuthTransactionKind.OAUTH_STATE, token) == {"nonce": "secret"}
    assert auth_transaction_manager.consume(AuthTransactionKind.OAUTH_STATE, token) is None


@pytest.mark.usefixtures("memory_redis")
def test_transaction_kinds_are_isolated() -> None:
    token = auth_transaction_manager.create(AuthTransactionKind.OAUTH_STATE, {"provider_id": 4}, 60)

    assert auth_transaction_manager.peek(AuthTransactionKind.REDIRECT_REDEMPTION, token) is None
    assert auth_transaction_manager.consume(AuthTransactionKind.REDIRECT_REDEMPTION, token) is None
    assert auth_transaction_manager.consume(AuthTransactionKind.OAUTH_STATE, token) == {"provider_id": 4}


@pytest.mark.usefixtures("memory_redis")
def test_only_one_concurrent_consumer_wins() -> None:
    token = auth_transaction_manager.create(AuthTransactionKind.REDIRECT_REDEMPTION, {"response": {"access_token": "jwt"}}, 60)

    with ThreadPoolExecutor(max_workers=8) as executor:
        results = list(executor.map(lambda _: auth_transaction_manager.consume(AuthTransactionKind.REDIRECT_REDEMPTION, token), range(16)))

    assert results.count({"response": {"access_token": "jwt"}}) == 1
    assert results.count(None) == 15


def test_malformed_handles_do_not_reach_redis(memory_redis: MemoryRedis) -> None:
    assert auth_transaction_manager.peek(AuthTransactionKind.OAUTH_STATE, "not-a-valid-token") is None
    assert auth_transaction_manager.consume(AuthTransactionKind.OAUTH_STATE, "x" * 10_000) is None
    assert memory_redis.get_calls == 0
    assert memory_redis.getdel_calls == 0


def test_oversized_or_non_json_payload_is_rejected(memory_redis: MemoryRedis) -> None:
    with pytest.raises(ValueError, match="exceeds"):
        auth_transaction_manager.create(
            AuthTransactionKind.OAUTH_STATE,
            {"value": "x" * auth_transaction_manager.MAX_SERIALIZED_BYTES},
            60,
        )
    with pytest.raises(ValueError, match="JSON serializable"):
        auth_transaction_manager.create(AuthTransactionKind.OAUTH_STATE, {"value": object()}, 60)
    assert memory_redis.values == {}


@pytest.mark.parametrize(
    "raw",
    [
        b"not-json",
        b'{"version":1,"kind":"oauth_state","payload":[]}',
        b"x" * (auth_transaction_manager.MAX_SERIALIZED_BYTES + 1),
    ],
)
def test_malformed_or_oversized_stored_envelope_fails_closed(memory_redis: MemoryRedis, raw: bytes) -> None:
    token = "A" * auth_transaction_manager.TOKEN_LENGTH
    key = f"{auth_transaction_manager.KEY_PREFIX}:{AuthTransactionKind.OAUTH_STATE.value}:{token}"
    memory_redis.values[key] = raw

    assert auth_transaction_manager.peek(AuthTransactionKind.OAUTH_STATE, token) is None
    assert auth_transaction_manager.consume(AuthTransactionKind.OAUTH_STATE, token) is None


@pytest.mark.parametrize("ttl", [0, -1, auth_transaction_manager.MAX_TTL_SECONDS + 1, True])
@pytest.mark.usefixtures("memory_redis")
def test_invalid_ttl_is_rejected(ttl: int) -> None:
    with pytest.raises(ValueError, match="TTL"):
        auth_transaction_manager.create(AuthTransactionKind.OAUTH_STATE, {}, ttl)
