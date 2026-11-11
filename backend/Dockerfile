FROM python:3.12.16-slim-trixie

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    UV_LINK_MODE=copy \
    UV_COMPILE_BYTECODE=1 \
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    PATH="/opt/venv/bin:$PATH" \
    DATA_DIR=/data

RUN pip install --no-cache-dir uv==0.13.7

# Utilisateur non root ; /data est créé ici pour que le volume nommé en hérite les droits.
RUN useradd --system --uid 10001 --create-home app \
    && mkdir -p /app /data /opt/venv \
    && chown -R app:app /app /data /opt/venv

WORKDIR /app
USER app

# Dépendances d'abord : cette couche ne change que si pyproject.toml ou uv.lock changent.
COPY --chown=app:app pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

COPY --chown=app:app alembic.ini ./
COPY --chown=app:app alembic ./alembic
COPY --chown=app:app app ./app
COPY --chown=app:app --chmod=755 docker-entrypoint.sh ./docker-entrypoint.sh

VOLUME ["/data"]
EXPOSE 8000

# /api/v1/health répond toujours 200 ; le délai couvre la vérification JSON de SearXNG (D29).
HEALTHCHECK --interval=15s --timeout=20s --start-period=30s --retries=5 \
    CMD ["python", "-c", "import urllib.request as u; u.urlopen('http://127.0.0.1:8000/api/v1/health', timeout=18)"]

ENTRYPOINT ["./docker-entrypoint.sh"]
