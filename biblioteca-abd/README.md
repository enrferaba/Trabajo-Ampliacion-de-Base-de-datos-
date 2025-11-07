# Biblioteca ABD

Biblioteca ABD es una plataforma de biblioteca online que combina Django + Django REST Framework, MongoDB y Neo4j para ofrecer catálogo, reseñas y recomendaciones en tiempo real. El proyecto está pensado como base para equipos que necesitan un stack moderno con tareas en segundo plano (Celery), cache distribuida (Redis) y despliegue con Docker Compose.

## Objetivos
- Gestionar el catálogo de libros y autores, incluyendo búsqueda y filtrado avanzado.
- Permitir a las personas usuarias publicar reseñas con valoraciones moderadas por rate limiting.
- Generar recomendaciones item-item y personalizadas utilizando un grafo en Neo4j.
- Ejecutar importaciones masivas de libros desde CSV/JSON en segundo plano.
- Proveer observabilidad, healthcheck, documentación OpenAPI y buenas prácticas de DX (pre-commit, pruebas, seeds).

## Arquitectura
- **Django 5 + DRF** para la API REST.
- **MongoDB** como base documental para libros, autores, usuarios y reseñas.
- **Neo4j** como base grafo para recomendaciones y relaciones semánticas.
- **Redis** como cache, rate limiting y broker de Celery.
- **Celery** para tareas asíncronas (importaciones, recomputo de métricas, recomendaciones).
- **Docker Compose** orquesta web, worker, beat, Redis, Mongo, Neo4j y Flower.
- **drf-spectacular** expone la documentación OpenAPI en `/api/schema/swagger/` y `/api/schema/redoc/`.

![Arquitectura](docs/arquitectura.mmd)

## Requisitos previos
- Docker y Docker Compose v2
- GNU Make (opcional pero recomendado)
- Python 3.12 si se ejecuta fuera de contenedores

## Configuración rápida
```bash
cp .env.example .env
make up
```
La primera ejecución construye las imágenes, migra la base de datos SQLite interna y levanta todos los servicios.

### Servicios expuestos
| Servicio | URL | Descripción |
|----------|-----|-------------|
| Django | http://localhost:8000 | API REST y documentación OpenAPI |
| Flower | http://localhost:5555 | Monitoreo de tareas Celery |
| Neo4j Browser | http://localhost:7474 | Exploración del grafo |

## Variables de entorno
Ver `.env.example` para la lista completa. Variables clave:
- `DJANGO_SECRET_KEY`, `DEBUG`
- `REDIS_URL`, `CACHE_TTL_SECONDS`, `RATE_LIMIT_*`
- `MONGO_URL`, `MONGO_DB`
- `NEO4J_URI`, `NEO4J_USER`, `NEO4J_PASSWORD`
- `CELERY_BROKER_URL`, `CELERY_RESULT_BACKEND`

## Comandos Make
| Comando | Descripción |
|---------|-------------|
| `make up` | Construye y levanta todos los servicios |
| `make down` | Detiene y elimina contenedores/volúmenes |
| `make logs` | Sigue logs de todos los servicios |
| `make test` | Ejecuta la suite de pytest |
| `make lint` | Ejecuta pre-commit en todo el código |
| `make format` | Aplica black + isort |
| `make seed` | Ejecuta `python manage.py seed_data` para datos demo |

## Endpoints principales
- Salud: `GET /health`
- Documentación: `GET /api/schema/swagger/`, `GET /api/schema/redoc/`
- Catálogo:
  - `GET /api/books?q=&author_id=&genres=&sort=rating|popularity&order=asc|desc&page=&page_size=`
  - `POST /api/books` (administración)
  - `GET /api/books/{id}`
  - `PATCH /api/books/{id}`
  - `DELETE /api/books/{id}` (borrado lógico)
  - `GET /api/authors?q=&page=&page_size=`
- Reseñas:
  - `POST /api/reviews {book_id, rating, text}` (rating 1..5 + anti-spam Redis)
  - `GET /api/books/{id}/reviews`
  - `PATCH /api/reviews/{id}`
  - `DELETE /api/reviews/{id}` (borrado lógico)
- Recomendaciones:
  - `GET /api/reco/books/{id}/similar?top_k=10`
  - `GET /api/reco/users/{id}/personalized?top_k=10`
- Ingesta:
  - `POST /api/import/books` (subir CSV/JSON)
  - `GET /api/import/status/{task_id}`

### Ejemplos curl
```bash
curl http://localhost:8000/health
curl "http://localhost:8000/api/books?q=ficcion&genres=Fantasía"
curl -X POST http://localhost:8000/api/reviews \
  -H "Content-Type: application/json" \
  -d '{"book_id": "book-1", "rating": 5, "text": "Excelente"}'
```

## Modelado de datos MongoDB
- `books`: `_id`, `title`, `authors`, `genres`, `year`, `isbn`, `synopsis`, `cover_url`, `avg_rating`, `rating_count`, `created_at`, `updated_at`
- `authors`: `_id`, `name`, `bio`, `created_at`
- `users`: `_id`, `username`, `email`, `password_hash`, `created_at`
- `reviews`: `_id`, `user_id`, `book_id`, `rating`, `text`, `created_at`, `deleted_at`

Índices clave: búsqueda de texto en `title/synopsis`, compuestos en `genres/year`, ordenamiento por `avg_rating` y `rating_count`, índice único `(user_id, book_id)` para reseñas.

## Grafo Neo4j
Nodos: `Book`, `Author`, `Genre`, `User`.
Relaciones:
- `(Author)-[:WROTE]->(Book)`
- `(Book)-[:HAS_GENRE]->(Genre)`
- `(User)-[:REVIEWED {rating}] -> (Book)`
- `(Book)-[:SIMILAR_TO {score}]-(Book)`

Constraints sugeridos en `id` de `Book`, `Author`, `User` y nombre de `Genre`.

## Claves Redis
- `cache:books:list:{hash}` → TTL `CACHE_TTL_SECONDS`
- `ratelimit:{scope}:{key}:{window}` → contador con expiración
- `antispam:reviews:{user_id}` → ventana deslizante
- Canal pub/sub `events:biblioteca`

## Tareas Celery
- `apps.ingestion.tasks.import_books_from_csv`
- `apps.ingestion.tasks.import_books_from_json`
- `apps.reviews.tasks.recompute_book_stats`
- `apps.reco.tasks.recompute_similar_books`

Celery se ejecuta con `CELERY_TASK_ALWAYS_EAGER=1` por defecto en entornos de desarrollo para facilitar pruebas. Ajustar en `.env` para producción.

## Calidad y DX
- `pytest` + `pytest-django`
- `pre-commit` con black, ruff e isort
- Logging estructurado con `structlog`
- Colección Postman en `docs/postman_collection.json`

## Pruebas
```bash
make test
```

## Seeds y datasets
```bash
make seed
```
El comando utiliza `mongo_service` con fallback en memoria para cargar autores y libros de ejemplo.

## Troubleshooting
- **Celery no recibe tareas**: revisar `CELERY_BROKER_URL` y `CELERY_RESULT_BACKEND` apuntando a Redis.
- **Mongo/Neo4j no responden**: confirmar puertos expuestos (`27017`, `7687/7474`) y credenciales en `.env`.
- **OpenAPI vacío**: ejecutar `docker compose logs web` para comprobar migraciones y dependencias.
- **Importaciones fallan**: asegurar formato correcto de CSV/JSON y revisar logs del worker.

## Roadmap (10 días)
1. Implementar autenticación JWT completa y permisos por rol.
2. Añadir métricas Prometheus y dashboards Grafana.
3. Persistir tokens anti-spam por IP y usuario simultáneamente.
4. Agregar pipeline ETL para enriquecer libros con datos externos.
5. Implementar recomendaciones híbridas con embeddings.
6. Añadir filtros por disponibilidad y editoriales.
7. Integrar almacenamiento de portadas en S3 compatible.
8. Automatizar despliegues con GitHub Actions.
9. Añadir tests de contrato y colección Newman.
10. Incorporar búsquedas semánticas con OpenSearch.

## Licencia
Distribuido bajo licencia [MIT](LICENSE).
