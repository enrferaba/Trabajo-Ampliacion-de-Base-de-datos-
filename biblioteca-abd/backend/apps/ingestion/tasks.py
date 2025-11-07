from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any, Dict, Iterable

from celery import shared_task

from ..catalog.services.mongo_service import mongo_service


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
    for row in _load_csv(path_obj):
        mongo_service.create_book(row)
        imported += 1
    return {"imported": imported}


@shared_task(bind=True)
def import_books_from_json(self, path: str) -> Dict[str, Any]:
    path_obj = Path(path)
    imported = 0
    for row in _load_json(path_obj):
        mongo_service.create_book(row)
        imported += 1
    return {"imported": imported}
