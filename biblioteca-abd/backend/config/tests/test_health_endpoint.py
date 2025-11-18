from rest_framework.test import APIClient


def test_health_endpoint_accepts_optional_trailing_slash():
    client = APIClient()

    for url in ("/health", "/health/"):
        response = client.get(url)
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}
