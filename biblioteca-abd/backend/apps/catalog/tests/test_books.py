from django.urls import reverse
from rest_framework.test import APIClient
import pytest

from apps.catalog.services.mongo_service import mongo_service
from apps.catalog import views as catalog_views


@pytest.fixture(autouse=True)
def clear_catalog_memory():
    mongo_service._memory_books.clear()
    mongo_service._memory_authors.clear()
    yield
    mongo_service._memory_books.clear()
    mongo_service._memory_authors.clear()


def test_list_books_empty():
    client = APIClient()
    response = client.get(reverse("book-list"))
    assert response.status_code == 200
    assert response.data["results"] == []


def test_deleted_book_is_not_listed_or_retrieved():
    client = APIClient()
    create_response = client.post(
        reverse("book-list"),
        {
            "title": "Temporal Book",
            "authors": [{"id": "author-1", "name": "Author"}],
        },
        format="json",
    )
    assert create_response.status_code == 201
    book_id = create_response.data["_id"]

    delete_response = client.delete(reverse("book-detail", args=[book_id]))
    assert delete_response.status_code == 204

    list_response = client.get(reverse("book-list"))
    assert list_response.status_code == 200
    ids = [book["_id"] for book in list_response.data["results"]]
    assert book_id not in ids

    detail_response = client.get(reverse("book-detail", args=[book_id]))
    assert detail_response.status_code == 404


def test_cache_is_invalidated_when_book_is_deleted(monkeypatch):
    cache_store: dict[str, dict] = {}

    def fake_get(key):
        return cache_store.get(key)

    def fake_set(key, value, ttl=None):
        cache_store[key] = value

    def fake_invalidate():
        cache_store.clear()

    monkeypatch.setattr(catalog_views, "cache_get", fake_get)
    monkeypatch.setattr(catalog_views, "cache_set", fake_set)
    monkeypatch.setattr(catalog_views, "invalidate_books_cache", fake_invalidate)

    client = APIClient()
    create_response = client.post(
        reverse("book-list"),
        {"title": "Cached Book", "authors": [{"id": "author-2", "name": "Author"}]},
        format="json",
    )
    assert create_response.status_code == 201
    book_id = create_response.data["_id"]

    first_list = client.get(reverse("book-list"))
    assert first_list.status_code == 200
    assert any(book["_id"] == book_id for book in first_list.data["results"])
    assert cache_store  # cache populated

    delete_response = client.delete(reverse("book-detail", args=[book_id]))
    assert delete_response.status_code == 204
    assert cache_store == {}

    list_response = client.get(reverse("book-list"))
    assert list_response.status_code == 200
    ids = [book["_id"] for book in list_response.data["results"]]
    assert book_id not in ids

    detail_response = client.get(reverse("book-detail", args=[book_id]))
    assert detail_response.status_code == 404
