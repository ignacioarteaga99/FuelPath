FROM python:3.12-slim

WORKDIR /app
COPY pyproject.toml README.md LICENSE ./
COPY fuelpath/ fuelpath/
COPY web/ web/
RUN pip install --no-cache-dir -e .

# Menos «arenas» de memoria por hilo (lección de PacePath en 512 MB).
ENV MALLOC_ARENA_MAX=2
ENV PORT=8000
EXPOSE 8000

# PORT lo fija Render (10000); en local queda en 8000.
CMD ["sh", "-c", "exec python -m uvicorn fuelpath.api:app --host 0.0.0.0 --port ${PORT}"]
