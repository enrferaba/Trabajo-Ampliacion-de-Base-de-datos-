from __future__ import annotations

from django.conf import settings
from django.contrib.auth.models import User
from django.core import signing
from rest_framework import authentication, exceptions

from .services.redis_service import cache_get


class SignedTokenAuthentication(authentication.BaseAuthentication):
    """Autenticación basada en tokens firmados y almacenados en Redis."""

    def authenticate(self, request):
        token = request.headers.get("Authorization")
        if not token:
            return None

        signer = signing.TimestampSigner()
        max_age = getattr(settings, "AUTH_TOKEN_TTL_SECONDS", 86400)
        try:
            user_pk = signer.unsign(token, max_age=max_age)
        except signing.SignatureExpired as exc:
            raise exceptions.AuthenticationFailed("Token expirado") from exc
        except signing.BadSignature as exc:
            raise exceptions.AuthenticationFailed("Token inválido") from exc

        cached = cache_get(f"auth:token:{token}")
        if not cached:
            raise exceptions.AuthenticationFailed("Token no encontrado")

        cached_user_id = cached.get("user_id")
        if str(cached_user_id) != str(user_pk):
            raise exceptions.AuthenticationFailed("Token inválido")

        try:
            user = User.objects.get(pk=user_pk)
        except User.DoesNotExist as exc:
            raise exceptions.AuthenticationFailed("Usuario no encontrado") from exc

        return (user, token)
