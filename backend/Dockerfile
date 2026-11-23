FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ ./backend/
COPY data/ ./data/

ENV PYTHONPATH=/app/backend
EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

# This Dockerfile sets up a lightweight Python 3.11 environment for the ShopMind AI application. It installs necessary system dependencies, copies the application code and data into the container, installs Python dependencies from requirements.txt, and exposes port 8000 for the FastAPI server. The CMD instruction runs the Uvicorn server to serve the FastAPI application.
