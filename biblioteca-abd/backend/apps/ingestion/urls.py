from django.urls import path

from .views import ImportBooksView, ImportStatusView

urlpatterns = [
    path("import/books", ImportBooksView.as_view(), name="import-books"),
    path("import/status/<str:task_id>", ImportStatusView.as_view(), name="import-status"),
]
