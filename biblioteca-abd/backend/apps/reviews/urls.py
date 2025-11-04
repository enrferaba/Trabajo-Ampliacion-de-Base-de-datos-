from django.urls import path

from .views import review_create, review_list, review_update

urlpatterns = [
    path("reviews", review_create, name="review-create"),
    path("reviews/<str:pk>", review_update, name="review-update"),
    path("books/<str:book_id>/reviews", review_list, name="book-reviews"),
]
