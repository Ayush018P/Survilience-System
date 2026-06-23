# Base image with Python 3.11
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies required for OpenCV, PyTorch, and general build tools
RUN apt-get update && apt-get install -y \
    build-essential \
    libgl1 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first to leverage Docker cache
COPY requirements.txt .

# Install Python dependencies
# We use --no-cache-dir to keep the image small
RUN pip install --no-cache-dir -r requirements.txt

# Create necessary directories for offline storage
RUN mkdir -p /app/backend/data/models \
    /app/backend/data/photos \
    /app/backend/data/snapshots

# Copy the rest of the backend source code
# We assume the context is the neuroguard-ai root directory
COPY backend/ ./backend/

# Ensure the app has write permissions to the data directories
RUN chmod -R 777 /app/backend/data

# Expose the FastAPI port
EXPOSE 8000

# Set environment variables
ENV PYTHONPATH=/app
ENV HOST=0.0.0.0
ENV PORT=8000

# Command to run the application using uvicorn
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
