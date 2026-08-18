# Use official lightweight Python image
FROM python:3.11-slim

# Set environment variables for Python and Cloud Run
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8080 \
    GUNICORN_RUN=1

# Install system dependencies:
# - ffmpeg: audio decoding & Discord Opus voice streaming
# - libopus0: Discord Opus audio codec
# - libsndfile1: soundfile audio loader
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    libopus0 \
    libsndfile1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY . .

# Expose default Cloud Run port
EXPOSE 8080

# Run with Gunicorn (1 worker + 8 threads to allow concurrent Flask requests and async background Discord bot)
CMD exec gunicorn --bind 0.0.0.0:$PORT --workers 1 --threads 8 --timeout 0 app:app
