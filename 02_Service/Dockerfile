FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PORT=8080 \
    CHEMIN_BASE=/app/donnees/tete-de-brut.sqlite \
    CHEMIN_CAS=/app/cas

WORKDIR /app

COPY pyproject.toml ./
COPY app ./app
RUN pip install .

# Le cas enregistré (hors Git) est copié s'il existe dans le contexte de construction.
COPY cas ./cas

RUN useradd --system --create-home --uid 10001 service \
    && mkdir -p /app/donnees \
    && chown -R service:service /app/donnees
USER service

EXPOSE 8080

CMD ["sh", "-c", "exec python -m uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8080}"]
