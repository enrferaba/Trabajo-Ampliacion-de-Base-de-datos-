from django.urls import reverse
from rest_framework.test import APIClient


def test_import_books_requires_file():
    client = APIClient()
    response = client.post(reverse("import-books"))
    assert response.status_code == 400
