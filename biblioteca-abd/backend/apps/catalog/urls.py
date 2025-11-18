from django.urls import path

from .views import author_list, book_detail, book_list

urlpatterns = [
    path("books/", book_list, name="book-list"),
    path("books/<str:pk>/", book_detail, name="book-detail"),
    path("authors/", author_list, name="author-list"),
]
