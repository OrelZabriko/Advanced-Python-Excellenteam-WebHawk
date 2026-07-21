FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Unlike the other services, services/shared/ is not copied here: the
# middleware never touches Postgres and reads no environment variables, so it
# has no use for Config or the DB connection helper.
COPY middleware/ ./middleware/

EXPOSE 8080

CMD ["gunicorn", "--bind", "0.0.0.0:8080", "--workers", "4", "middleware.app:create_app()"]