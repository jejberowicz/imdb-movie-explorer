# Backend image. The API (Gunicorn) and the seed command run from it.
FROM python:3.12.15-slim-trixie AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

# Run as an unprivileged user, not as root.
RUN useradd --create-home --uid 10001 app
USER app

EXPOSE 8000
CMD ["gunicorn", "--config", "gunicorn.conf.py", "app.wsgi:app"]

# Same image plus the test and lint tools, for running the tests in Docker and in CI.
FROM runtime AS dev
USER root
COPY requirements-dev.txt .
RUN pip install -r requirements-dev.txt
USER app
CMD ["pytest"]
