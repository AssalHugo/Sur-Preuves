"""Tests unitaires pour le générateur d'identifiants UUIDv7 (csc.contracts.uuid_v7)."""

import concurrent.futures
import uuid

from csc.contracts.uuid_v7 import uuid7, uuid7_str


def test_uuid7_format_and_version() -> None:
    u = uuid7()
    assert isinstance(u, uuid.UUID)
    assert u.version == 7
    assert u.variant == uuid.RFC_4122

    s = uuid7_str()
    assert isinstance(s, str)
    parsed = uuid.UUID(s)
    assert parsed.version == 7


def test_uuid7_monotonicity() -> None:
    generated = [uuid7() for _ in range(200)]
    # Deux UUIDv7 générés séquentiellement doivent conserver l'ordre temporel
    assert generated == sorted(generated)


def test_uuid7_uniqueness() -> None:
    count = 1000
    ids = {uuid7() for _ in range(count)}
    assert len(ids) == count


def test_uuid7_multithread_safety() -> None:
    def worker() -> list[uuid.UUID]:
        return [uuid7() for _ in range(50)]

    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
        futures = [executor.submit(worker) for _ in range(4)]
        results = [f.result() for f in futures]

    all_ids = [item for sublist in results for item in sublist]
    assert len(set(all_ids)) == 200
