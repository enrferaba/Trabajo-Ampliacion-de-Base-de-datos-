from django.urls import reverse
from rest_framework.test import APIClient


def test_create_review_requires_valid_rating():
    client = APIClient()
    response = client.post(reverse("review-create"), {"book_id": "1", "rating": 6, "text": "oops"})
    assert response.status_code == 400
