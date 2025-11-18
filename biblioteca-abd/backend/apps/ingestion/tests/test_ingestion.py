import json

import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from apps.catalog.services.mongo_service import mongo_service
from apps.ingestion.tasks import import_books_from_csv, import_books_from_json


@pytest.fixture(autouse=True)
def clear_catalog_memory():
    mongo_service._memory_books.clear()
    yield
    mongo_service._memory_books.clear()


def test_import_books_requires_file():
    client = APIClient()
    response = client.post(reverse("import-books"))
    assert response.status_code == 400


def test_csv_import_task_removes_temp_file(tmp_path, monkeypatch):
    tmp_file = tmp_path / "books.csv"
    tmp_file.write_text("title\nTemporal Book\n")

    created = []

    def fake_create_book(data):
        created.append(data)

    monkeypatch.setattr(mongo_service, "create_book", fake_create_book)

    result = import_books_from_csv.run(str(tmp_file))

    assert result == {"imported": 1}
    assert created[0]["title"] == "Temporal Book"
    assert not tmp_file.exists()


def test_json_import_task_removes_temp_file_on_error(tmp_path, monkeypatch):
    tmp_file = tmp_path / "books.json"
    tmp_file.write_text(json.dumps([{"title": "Temporal Book"}]))

    def fail_create_book(_data):
        raise RuntimeError("boom")

    monkeypatch.setattr(mongo_service, "create_book", fail_create_book)

    with pytest.raises(RuntimeError):
        import_books_from_json.run(str(tmp_file))

    assert not tmp_file.exists()
