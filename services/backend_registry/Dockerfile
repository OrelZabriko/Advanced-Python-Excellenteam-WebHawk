FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY services/shared/ ./services/shared/
COPY services/backend_registry/ ./services/backend_registry/

EXPOSE 8080

CMD ["gunicorn", "--bind", "0.0.0.0:8080", "--workers", "4", "services.backend_registry.app:create_app()"]