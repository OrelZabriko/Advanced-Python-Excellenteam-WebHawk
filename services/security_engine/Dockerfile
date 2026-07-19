FROM python:3.11-slim

WORKDIR /app

COPY services/security-engine/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY services/security-engine/ .

ENV PYTHONPATH=/app

CMD ["python", "app.py"]
