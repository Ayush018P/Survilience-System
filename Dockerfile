# Hugging Face Spaces Dockerfile
# Spaces require the app to run on port 7860 and under a non-root user (id 1000)

FROM python:3.11-slim

# Create user with UID 1000
RUN useradd -m -u 1000 user
ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH

# Install system dependencies required for OpenCV
RUN apt-get update && apt-get install -y \
    libglib2.0-0 \
    libgl1 \
    libgl1-mesa-glx \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR $HOME/app

# Give the user ownership of the app directory
RUN chown -R user:user $HOME/app

# Switch to the non-root user
USER user

# Copy requirements and install
COPY --chown=user:user requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend source code
COPY --chown=user:user backend ./backend

# Create necessary directories
RUN mkdir -p $HOME/app/data/embeddings $HOME/app/data/photos $HOME/app/logs $HOME/app/snapshots $HOME/app/models

# Expose HF specific port
EXPOSE 7860

# Run uvicorn on port 7860
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "7860"]
