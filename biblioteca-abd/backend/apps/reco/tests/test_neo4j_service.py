from __future__ import annotations

from typing import Any, Dict, List

from apps.reco.services.neo4j_service import Neo4jService
from neo4j.exceptions import Neo4jError


class DummyRecord:
    def __init__(self, payload: Dict[str, Any]):
        self._payload = payload

    def data(self) -> Dict[str, Any]:
        return self._payload


class DummySession:
    def __init__(self, records: List[DummyRecord]):
        self._records = records

    def __enter__(self) -> "DummySession":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:  # pragma: no cover - nothing to clean up
        return None

    def run(self, query: str, **params):  # pragma: no cover - exercised in tests
        return self._records


class DummyDriver:
    def __init__(self, records: List[DummyRecord], *, raise_on_run: bool = False):
        self.records = records
        self.raise_on_run = raise_on_run
        self.closed = False
        self.session_calls = 0

    def verify_connectivity(self) -> None:  # pragma: no cover - nothing to do
        return None

    def session(self):
        self.session_calls += 1
        if self.raise_on_run:
            return FailingSession()
        return DummySession(self.records)

    def close(self):  # pragma: no cover - tracked via attribute
        self.closed = True


class FailingSession(DummySession):
    def __init__(self):  # pragma: no cover - no state
        super().__init__(records=[])

    def run(self, query: str, **params):
        raise Neo4jError("boom")


def test_driver_is_cached_across_queries(monkeypatch):
    call_count = 0
    dummy_driver = DummyDriver(
        [
            DummyRecord({
                "id": "2",
                "title": "Example",
                "cover_url": "http://example.com",
            })
        ]
    )

    def fake_driver(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        return dummy_driver

    monkeypatch.setattr("apps.reco.services.neo4j_service.GraphDatabase.driver", fake_driver)

    service = Neo4jService()

    assert service.similar_books("1")
    assert service.personalized_for_user("user")
    assert call_count == 1
    assert dummy_driver.session_calls == 2


def test_falls_back_to_memory_when_driver_unavailable(monkeypatch):
    def fake_driver(*args, **kwargs):
        raise OSError("no host")

    monkeypatch.setattr("apps.reco.services.neo4j_service.GraphDatabase.driver", fake_driver)
    service = Neo4jService()
    service._memory_graph["similar"].append(
        {
            "book_id": "1",
            "id": "2",
            "title": "Memory Book",
            "cover_url": "",
        }
    )
    results = service.similar_books("1")
    assert results == [{"id": "2", "title": "Memory Book", "cover_url": ""}]


def test_driver_resets_when_query_fails(monkeypatch):
    call_count = 0
    dummy_driver = DummyDriver([], raise_on_run=True)

    def fake_driver(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        return dummy_driver

    monkeypatch.setattr("apps.reco.services.neo4j_service.GraphDatabase.driver", fake_driver)

    service = Neo4jService()
    assert service.similar_books("1") == []
    assert service._driver is None
    assert call_count == 1

    service.similar_books("1")
    assert call_count == 2
