import pytest
from django.urls import reverse
from rest_framework.test import APIClient


@pytest.mark.django_db
def test_signup_and_login_flow():
    client = APIClient()
    signup_resp = client.post(reverse("signup"), {"username": "tester", "password": "secret"})
    assert signup_resp.status_code == 201

    login_resp = client.post(reverse("login"), {"username": "tester", "password": "secret"})
    assert login_resp.status_code == 200
    assert "token" in login_resp.data
