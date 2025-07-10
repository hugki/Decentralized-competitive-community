FROM python:3.11-slim

WORKDIR /app
ENV PYTHONUNBUFFERED=1

# deps
COPY apps/backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# src
COPY apps/backend /app/apps/backend

CMD ["uvicorn", "apps.backend.main:app", "--host", "0.0.0.0", "--port", "8080"]
