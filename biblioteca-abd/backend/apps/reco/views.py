from rest_framework import permissions, status, viewsets
from rest_framework.response import Response

from .services.neo4j_service import neo4j_service


class RecommendationViewSet(viewsets.ViewSet):
    permission_classes = [permissions.AllowAny]

    def retrieve(self, request, pk=None):
        top_k = int(request.query_params.get("top_k", 10))
        similar = neo4j_service.similar_books(pk, top_k=top_k)
        return Response({"results": similar})

    def list(self, request, user_id=None):
        top_k = int(request.query_params.get("top_k", 10))
        personalized = neo4j_service.personalized_for_user(user_id, top_k=top_k)
        return Response({"results": personalized})


similar_books_view = RecommendationViewSet.as_view({"get": "retrieve"})
personalized_view = RecommendationViewSet.as_view({"get": "list"})
