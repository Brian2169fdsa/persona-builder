FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["/bin/sh", "-c", "echo \"Starting persona-builder on port ${PORT:-8001}\" && python -c 'import app; print(\"Import OK\")' && exec uvicorn app:app --host 0.0.0.0 --port ${PORT:-8001}"]
