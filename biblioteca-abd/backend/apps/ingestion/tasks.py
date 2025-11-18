from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any, Dict, Iterable

from celery import shared_task
import structlog

from ..catalog.services.mongo_service import mongo_service


logger = structlog.get_logger(__name__)


def _load_csv(path: Path) -> Iterable[Dict[str, Any]]:
    with path.open() as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            yield row


def _load_json(path: Path) -> Iterable[Dict[str, Any]]:
    with path.open() as fh:
        data = json.load(fh)
    if isinstance(data, list):
        return data
    return data.get("items", [])


@shared_task(bind=True)
def import_books_from_csv(self, path: str) -> Dict[str, Any]:
    path_obj = Path(path)
    imported = 0
    try:
        for row in _load_csv(path_obj):
            mongo_service.create_book(row)
            imported += 1
        return {"imported": imported}
    finally:
        _cleanup_import_file(path_obj)


@shared_task(bind=True)
def import_books_from_json(self, path: str) -> Dict[str, Any]:
    path_obj = Path(path)
    imported = 0
    try:
        for row in _load_json(path_obj):
            mongo_service.create_book(row)
            imported += 1
        return {"imported": imported}
    finally:
        _cleanup_import_file(path_obj)


def _cleanup_import_file(path_obj: Path) -> None:
    try:
        path_obj.unlink()
    except FileNotFoundError:
        logger.info("import_task_cleanup", path=str(path_obj), removed=False, reason="missing")
    except OSError as exc:
        logger.warning(
            "import_task_cleanup_failed",
            path=str(path_obj),
            removed=False,
            error=str(exc),
        )
    else:
        logger.info("import_task_cleanup", path=str(path_obj), removed=True)
