import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from apps.authx.services import redis_service


@pytest.fixture(autouse=True)
def fake_redis_cache(monkeypatch):
    store: dict[str, dict] = {}

    def fake_set(key, value, ttl=None):
        store[key] = value

    def fake_get(key):
        return store.get(key)

    def fake_delete(key):
        store.pop(key, None)

    monkeypatch.setattr(redis_service, "cache_set", fake_set)
    monkeypatch.setattr(redis_service, "cache_get", fake_get)
    monkeypatch.setattr(redis_service, "cache_delete", fake_delete)
    # Actual views/auth classes import the functions directly, so patch them as well.
    import apps.authx.views as auth_views
    import apps.authx.authentication as auth_auth

    monkeypatch.setattr(auth_views, "cache_set", fake_set)
    monkeypatch.setattr(auth_views, "cache_delete", fake_delete)
    monkeypatch.setattr(auth_auth, "cache_get", fake_get)


@pytest.mark.django_db
def test_signup_and_login_flow():
    client = APIClient()
    signup_resp = client.post(reverse("signup"), {"username": "tester", "password": "secret"})
    assert signup_resp.status_code == 201

    login_resp = client.post(reverse("login"), {"username": "tester", "password": "secret"})
    assert login_resp.status_code == 200
    token = login_resp.data["token"]
    cached = redis_service.cache_get(f"auth:token:{token}")
    assert cached == {"user_id": login_resp.data["user_id"]}


@pytest.mark.django_db
def test_logout_requires_valid_token_and_removes_cache():
    client = APIClient()
    client.post(reverse("signup"), {"username": "tester", "password": "secret"})
    login_resp = client.post(reverse("login"), {"username": "tester", "password": "secret"})
    token = login_resp.data["token"]

    logout_resp = client.post(reverse("logout"), HTTP_AUTHORIZATION=token)
    assert logout_resp.status_code == 204
    assert redis_service.cache_get(f"auth:token:{token}") is None


@pytest.mark.django_db
def test_request_fails_when_token_missing_from_cache():
    client = APIClient()
    client.post(reverse("signup"), {"username": "tester", "password": "secret"})
    login_resp = client.post(reverse("login"), {"username": "tester", "password": "secret"})
    token = login_resp.data["token"]
    redis_service.cache_delete(f"auth:token:{token}")

    logout_resp = client.post(reverse("logout"), HTTP_AUTHORIZATION=token)
    assert logout_resp.status_code == status.HTTP_403_FORBIDDEN
    assert logout_resp.data["detail"] == "Token no encontrado"


@pytest.mark.django_db
def test_request_fails_when_token_expired(monkeypatch, settings):
    client = APIClient()
    client.post(reverse("signup"), {"username": "tester", "password": "secret"})
    login_resp = client.post(reverse("login"), {"username": "tester", "password": "secret"})
    token = login_resp.data["token"]

    import django.core.signing as signing_module

    current = signing_module.time.time()
    future = current + settings.AUTH_TOKEN_TTL_SECONDS + 1
    monkeypatch.setattr(signing_module.time, "time", lambda: future)

    logout_resp = client.post(reverse("logout"), HTTP_AUTHORIZATION=token)
    assert logout_resp.status_code == status.HTTP_403_FORBIDDEN
    assert logout_resp.data["detail"] == "Token expirado"
