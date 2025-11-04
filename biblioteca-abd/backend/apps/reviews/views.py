from rest_framework import permissions, status, viewsets
from rest_framework.response import Response

from ..authx.services.redis_service import anti_spam_check
from .services.mongo_reviews import mongo_reviews
from .tasks import recompute_book_stats


class ReviewViewSet(viewsets.ViewSet):
    permission_classes = [permissions.AllowAny]

    def create(self, request):
        rating = request.data.get("rating")
        try:
            rating_value = int(rating)
        except (TypeError, ValueError):
            return Response({"detail": "rating debe estar entre 1 y 5"}, status=status.HTTP_400_BAD_REQUEST)
        if rating_value < 1 or rating_value > 5:
            return Response({"detail": "rating debe estar entre 1 y 5"}, status=status.HTTP_400_BAD_REQUEST)
        user_id = str(request.data.get("user_id", "anon"))
        if anti_spam_check(user_id):
            return Response({"detail": "demasiadas reseñas en poco tiempo"}, status=status.HTTP_429_TOO_MANY_REQUESTS)
        payload = dict(request.data)
        payload["rating"] = rating_value
        review = mongo_reviews.create_review(payload)
        recompute_book_stats.delay(review.get("book_id"))
        return Response(review, status=status.HTTP_201_CREATED)

    def list(self, request, book_id=None):
        reviews = mongo_reviews.list_reviews_for_book(book_id)
        return Response({"results": reviews, "count": len(reviews)})

    def partial_update(self, request, pk=None):
        updated = mongo_reviews.update_review(pk, request.data)
        if not updated:
            return Response(status=status.HTTP_404_NOT_FOUND)
        recompute_book_stats.delay(updated.get("book_id"))
        return Response(updated)

    def destroy(self, request, pk=None):
        removed = mongo_reviews.delete_review(pk)
        if not removed:
            return Response(status=status.HTTP_404_NOT_FOUND)
        return Response(status=status.HTTP_204_NO_CONTENT)


review_create = ReviewViewSet.as_view({"post": "create"})
review_update = ReviewViewSet.as_view({"patch": "partial_update", "delete": "destroy"})
review_list = ReviewViewSet.as_view({"get": "list"})
