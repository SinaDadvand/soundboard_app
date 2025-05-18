FROM python:3.9-slim

# Install required system dependencies for keyboard and audio support
RUN apt-get update && apt-get install -y \
    python3-dev \
    libasound2-dev \
    portaudio19-dev \
    python3-pyaudio \
    libsdl2-2.0-0 \
    libsdl2-mixer-2.0-0 \
    libglib2.0-0 \
    libsndfile1 \
    pulseaudio \
    alsa-utils \
    && rm -rf /var/lib/apt/lists/*

# Set up PulseAudio environment
ENV PULSE_SERVER=host.docker.internal
ENV PULSE_COOKIE=/tmp/pulse/cookie

WORKDIR /app

# Copy requirements first to leverage Docker cache
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application code
COPY . .

# Create audio directory if it doesn't exist
RUN mkdir -p static/audio

# Expose the port the app runs on
EXPOSE 5000

# Command to run the application
CMD ["python", "app.py"]
