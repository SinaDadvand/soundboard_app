# Use Python 3.11 slim image for smaller size
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install system dependencies (minimal, no audio drivers needed)
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements_container.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements_container.txt

# Copy application code
COPY app_container.py .
COPY static/ ./static/
COPY templates/ ./templates/

# Create audio directory (will be mounted as volume)
RUN mkdir -p static/audio

# Expose port
EXPOSE 5000

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:5000/ || exit 1

# Run the application
CMD ["python", "app_container.py"]
