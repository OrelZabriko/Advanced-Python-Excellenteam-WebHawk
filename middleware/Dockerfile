FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# services/shared/ is copied for error_handlers.py only - the middleware
# still has no database and no environment variables of its own. Copying
# config.py alongside it is harmless because nothing here imports it, and an
# unimported module never runs: error_handlers.py deliberately imports only
# flask and logging, so Config's DB_PASSWORD check never fires in this image.
COPY services/shared/ ./services/shared/
COPY middleware/ ./middleware/

EXPOSE 8080

CMD ["gunicorn", "--bind", "0.0.0.0:8080", "--workers", "4", "middleware.app:create_app()"]