from django.conf import settings
from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from django.core import signing
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .authentication import SignedTokenAuthentication
from .services.redis_service import cache_delete, cache_set


class SignupView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        username = request.data.get("username")
        password = request.data.get("password")
        if not username or not password:
            return Response({"detail": "username y password requeridos"}, status=status.HTTP_400_BAD_REQUEST)
        if User.objects.filter(username=username).exists():
            return Response({"detail": "usuario ya existe"}, status=status.HTTP_400_BAD_REQUEST)
        user = User.objects.create_user(username=username, password=password)
        return Response({"id": user.id, "username": user.username}, status=status.HTTP_201_CREATED)


class LoginView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        username = request.data.get("username")
        password = request.data.get("password")
        user = authenticate(username=username, password=password)
        if user is None:
            return Response({"detail": "credenciales invalidas"}, status=status.HTTP_400_BAD_REQUEST)
        token = signing.TimestampSigner().sign(user.pk)
        cache_set(
            f"auth:token:{token}",
            {"user_id": user.pk},
            ttl=getattr(settings, "AUTH_TOKEN_TTL_SECONDS", 86400),
        )
        return Response({"token": token, "user_id": user.pk})


class LogoutView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [SignedTokenAuthentication]

    def post(self, request):
        token = request.headers.get("Authorization")
        if token:
            cache_delete(f"auth:token:{token}")
        return Response(status=status.HTTP_204_NO_CONTENT)
