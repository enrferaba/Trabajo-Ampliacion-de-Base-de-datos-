from typing import Any, Dict

from rest_framework import permissions, status, viewsets
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response

from ..authx.services.redis_service import (
    cache_get,
    cache_key_for_books,
    cache_set,
    invalidate_books_cache,
)
from .services.mongo_service import mongo_service


class StandardResultsSetPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100


class BookViewSet(viewsets.ViewSet):
    permission_classes = [permissions.AllowAny]
    pagination_class = StandardResultsSetPagination

    def list(self, request):
        params = {
            "q": request.query_params.get("q"),
            "author_id": request.query_params.get("author_id"),
            "genres": request.query_params.get("genres"),
            "sort": request.query_params.get("sort", "rating"),
            "order": request.query_params.get("order", "desc"),
            "page": int(request.query_params.get("page", 1)),
            "page_size": int(request.query_params.get("page_size", 20)),
        }
        cache_key = cache_key_for_books(params)
        cached = cache_get(cache_key)
        if cached is not None:
            return Response(cached)

        filters: Dict[str, Any] = {}
        if params["q"]:
            filters["title"] = params["q"]
        if params["author_id"]:
            filters["authors.id"] = params["author_id"]
        if params["genres"]:
            filters["genres"] = params["genres"].split(",")
        filters["deleted"] = {"$ne": True}

        page = params["page"]
        page_size = params["page_size"]
        skip = (page - 1) * page_size
        books = mongo_service.list_books(filters, params["sort"], params["order"], skip, page_size)
        response_data = {
            "results": books,
            "page": page,
            "page_size": page_size,
            "count": len(books),
        }
        cache_set(cache_key, response_data)
        return Response(response_data)

    def retrieve(self, request, pk=None):
        book = mongo_service.get_book(pk)
        if not book:
            return Response(status=status.HTTP_404_NOT_FOUND)
        return Response(book)

    def create(self, request):
        book = mongo_service.create_book(request.data)
        return Response(book, status=status.HTTP_201_CREATED)

    def partial_update(self, request, pk=None):
        updated = mongo_service.update_book(pk, request.data)
        if not updated:
            return Response(status=status.HTTP_404_NOT_FOUND)
        return Response(updated)

    def destroy(self, request, pk=None):
        updated = mongo_service.update_book(pk, {"deleted": True})
        if not updated:
            return Response(status=status.HTTP_404_NOT_FOUND)
        invalidate_books_cache()
        return Response(status=status.HTTP_204_NO_CONTENT)


class AuthorViewSet(viewsets.ViewSet):
    permission_classes = [permissions.AllowAny]

    def list(self, request):
        params = {
            "q": request.query_params.get("q"),
            "page": int(request.query_params.get("page", 1)),
            "page_size": int(request.query_params.get("page_size", 20)),
        }
        filters: Dict[str, Any] = {}
        if params["q"]:
            filters["name"] = params["q"]
        skip = (params["page"] - 1) * params["page_size"]
        authors = mongo_service.list_authors(filters, skip, params["page_size"])
        return Response({"results": authors, "count": len(authors)})

    def create(self, request):
        author = mongo_service.create_author(request.data)
        return Response(author, status=status.HTTP_201_CREATED)


book_list = BookViewSet.as_view({"get": "list", "post": "create"})
book_detail = BookViewSet.as_view({"get": "retrieve", "patch": "partial_update", "delete": "destroy"})
author_list = AuthorViewSet.as_view({"get": "list", "post": "create"})
