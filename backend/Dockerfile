FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Cloud Run injects $PORT (defaults to 8080)
ENV PORT=8080
CMD exec uvicorn main:app --host 0.0.0.0 --port ${PORT}
