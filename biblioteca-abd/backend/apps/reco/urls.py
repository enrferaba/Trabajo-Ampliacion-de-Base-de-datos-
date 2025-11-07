from django.urls import path

from .views import personalized_view, similar_books_view

urlpatterns = [
    path("reco/books/<str:pk>/similar", similar_books_view, name="reco-books-similar"),
    path("reco/users/<str:user_id>/personalized", personalized_view, name="reco-users-personalized"),
]
