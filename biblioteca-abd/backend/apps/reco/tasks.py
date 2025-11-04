from __future__ import annotations

from celery import shared_task

from .services.neo4j_service import neo4j_service


@shared_task
def recompute_similar_books(book_id: str | None, top_k: int = 10) -> None:
    # Placeholder implementation. In a real scenario we would fetch co-occurrence stats from MongoDB.
    if book_id:
        neo4j_service.upsert_similarity(book_id, [])
    return None


@shared_task
def recompute_book_stats(book_id: str) -> None:
    # Deprecated alias maintained for backwards compatibility.
    return None
