from django.urls import reverse
from rest_framework.test import APIClient


def test_list_books_empty():
    client = APIClient()
    response = client.get(reverse("book-list"))
    assert response.status_code == 200
    assert response.data["results"] == []
