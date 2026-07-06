# Minimal container for Cloud Run / any container host.
# The app is stateless and keyless — no build args or secrets needed.
FROM python:3.12-slim

WORKDIR /app

# Install deps first (cached layer): copy only what pip needs to resolve the
# package, then the sources it references in [tool.hatch.build].
COPY pyproject.toml README.md ./
COPY meteo_aggregator ./meteo_aggregator
COPY api ./api
RUN pip install --no-cache-dir .

# Cloud Run injects $PORT (defaults to 8080); bind to it on all interfaces.
ENV PORT=8080
CMD ["sh", "-c", "exec uvicorn api.main:app --host 0.0.0.0 --port ${PORT}"]
