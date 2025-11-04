import tempfile
from pathlib import Path

from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from config.celery import app as celery_app
from .tasks import import_books_from_csv, import_books_from_json


class ImportBooksView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        upload = request.FILES.get("file")
        if not upload:
            return Response({"detail": "archivo requerido"}, status=status.HTTP_400_BAD_REQUEST)
        suffix = Path(upload.name).suffix.lower()
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            for chunk in upload.chunks():
                tmp.write(chunk)
            tmp_path = Path(tmp.name)
        if suffix == ".csv":
            task = import_books_from_csv.delay(str(tmp_path))
        else:
            task = import_books_from_json.delay(str(tmp_path))
        return Response({"task_id": task.id}, status=status.HTTP_202_ACCEPTED)


class ImportStatusView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request, task_id: str):
        result = celery_app.AsyncResult(task_id)
        if result.successful():
            return Response({"state": result.state, "result": result.result})
        return Response({"state": result.state})
