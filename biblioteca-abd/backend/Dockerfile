FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DJANGO_SETTINGS_MODULE=config.settings

WORKDIR /app

# Avoid relying on Debian mirrors that may not be reachable in some environments.
# The base image already ships with the build tools required for pure-Python wheels,
# so we only upgrade pip tooling here.
RUN python -m pip install --no-cache-dir --upgrade pip setuptools wheel

COPY requirements.txt ./
RUN python -m pip install --no-cache-dir -r requirements.txt

COPY . ./

CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
