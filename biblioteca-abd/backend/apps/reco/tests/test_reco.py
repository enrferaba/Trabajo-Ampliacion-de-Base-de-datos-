from django.urls import reverse
from rest_framework.test import APIClient


def test_similar_books_endpoint():
    client = APIClient()
    url = reverse("reco-books-similar", kwargs={"pk": "1"})
    response = client.get(url)
    assert response.status_code == 200
    assert "results" in response.data
