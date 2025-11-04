from django.core.management.base import BaseCommand

from ...services.mongo_service import mongo_service


class Command(BaseCommand):
    help = "Carga datos de ejemplo en MongoDB (o memoria si Mongo no está disponible)."

    def handle(self, *args, **options):
        authors = [
            {"_id": "auth-1", "name": "Isabel Allende"},
            {"_id": "auth-2", "name": "Jorge Luis Borges"},
        ]
        books = [
            {
                "_id": "book-1",
                "title": "La casa de los espíritus",
                "authors": [{"id": "auth-1", "name": "Isabel Allende"}],
                "genres": ["Realismo mágico"],
                "year": 1982,
                "avg_rating": 4.5,
                "rating_count": 1200,
            },
            {
                "_id": "book-2",
                "title": "Ficciones",
                "authors": [{"id": "auth-2", "name": "Jorge Luis Borges"}],
                "genres": ["Fantasía"],
                "year": 1944,
                "avg_rating": 4.7,
                "rating_count": 980,
            },
        ]
        for author in authors:
            mongo_service.create_author(author)
        for book in books:
            mongo_service.create_book(book)
        self.stdout.write(self.style.SUCCESS("Datos de ejemplo cargados"))
