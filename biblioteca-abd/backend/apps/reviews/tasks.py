from __future__ import annotations

from celery import shared_task


@shared_task
def recompute_book_stats(book_id: str) -> None:
    # Placeholder for future aggregation over MongoDB reviews collection.
    return None
