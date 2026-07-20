FROM python:3.11-slim

WORKDIR /app

COPY services/security_engine/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY services/security_engine/ .

ENV PYTHONPATH=/app

CMD ["python", "app.py"]