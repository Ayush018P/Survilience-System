FROM python:3.11-slim

WORKDIR /app

# Install system dependencies required for OpenCV and compiling
RUN apt-get update && apt-get install -y \
    libglib2.0-0 \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements from root context
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend source code
COPY backend ./backend

# Create necessary directories for storage
RUN mkdir -p /app/data/embeddings /app/data/photos /app/logs /app/snapshots /app/models

# Set environment variables for production
ENV PYTHONUNBUFFERED=1
ENV BACKEND_HOST=0.0.0.0
ENV BACKEND_PORT=8000

# Expose port
EXPOSE 8000

# Run FastAPI using Uvicorn
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
