from django.urls import reverse
from rest_framework.test import APIClient
import pytest

from apps.catalog.services.mongo_service import mongo_service


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
