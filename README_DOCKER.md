# Soundboard App - Docker Container Version

## Container Overview

This containerized version of the soundboard app uses **web-based audio playback** instead of system-level audio drivers, making it compatible with any Docker environment. Audio plays through your web browser using the Web Audio API.

## Key Features

- 🎵 **Web-based audio playback** - No system audio dependencies
- ⌨️ **Browser hotkey support** - Hotkeys work when browser tab is focused
- 🐳 **Universal Docker compatibility** - Runs on any system with Docker
- 📦 **Lightweight container** - Only Flask and minimal dependencies
- 🔄 **Volume mounting** - Easy to add/remove audio files

## Quick Start

### Option 1: Using Docker Compose (Recommended)

```bash
# Start the container
docker-compose up -d

# View logs
docker-compose logs -f

# Stop the container
docker-compose down
```

### Option 2: Using Docker Commands

```bash
# Build the image
docker build -t soundboard-container .

# Run the container
docker run -d \
  --name soundboard \
  -p 5000:5000 \
  -v ./static/audio:/app/static/audio:ro \
  soundboard-container

# View logs
docker logs soundboard

# Stop and remove
docker stop soundboard && docker rm soundboard
```

## Access the Application

Once running, open your browser and go to:
- **http://localhost:5000**
- **http://127.0.0.1:5000**

## How It Works

### Audio Playback
- **Container**: Serves audio files via HTTP
- **Browser**: Plays audio using Web Audio API
- **No pygame dependency** in container
- **Cross-platform compatibility**

### Hotkey Support
- **Ctrl + number keys** for first 11 sounds
- **Alt + number keys** for second 11 sounds  
- **Ctrl + Alt + number keys** for remaining sounds
- **Browser tab must be focused** for hotkeys to work

### File Structure in Container
```
/app/
├── app_container.py          # Container-optimized Flask app
├── templates/
│   └── index_container.html  # Container-specific template
├── static/
│   ├── js/
│   │   └── soundboard_container.js  # Web Audio API implementation
│   ├── css/
│   │   └── style.css
│   └── audio/               # Audio files (volume mounted)
│       ├── sound1.mp3
│       └── ...
└── requirements_container.txt  # Minimal dependencies
```

## Managing Audio Files

### Adding New Sounds
```bash
# Copy audio files to the audio directory
cp new_sound.mp3 ./static/audio/

# Restart container to reload sound mappings
docker-compose restart
```

### Supported Formats
- MP3, WAV, OGG
- Browser-compatible audio formats

## Configuration

### Environment Variables
- `FLASK_ENV=production` (default in docker-compose)

### Port Mapping
- Container exposes port `5000`
- Maps to host port `5000` by default
- Customizable in docker-compose.yml

## Health Check

The container includes a built-in health check:
```bash
# Check container health
docker ps
# Look for "healthy" status

# Manual health check
curl http://localhost:5000/
```

## Differences from Host Version

| Feature | Host Version | Container Version |
|---------|-------------|-------------------|
| Audio Playback | pygame mixer | Web Audio API |
| Hotkeys | Global system hotkeys | Browser-focused hotkeys |
| Dependencies | pygame, keyboard | Flask only |
| Platform | Windows-specific | Universal |
| Installation | Virtual environment | Docker container |

## Troubleshooting

### Container Won't Start
```bash
# Check container logs
docker logs soundboard-app_2-soundboard-1

# Check if port is in use
netstat -an | findstr :5000
```

### Audio Not Playing
1. Ensure browser allows autoplay
2. Click anywhere on page to initialize audio
3. Check browser console for errors
4. Verify audio files are properly mounted

### Hotkeys Not Working
1. Make sure browser tab is focused
2. Check browser console for JavaScript errors
3. Try clicking on page first to give it focus

## Development

### Building for Development
```bash
# Build with development settings
docker build -t soundboard-dev .

# Run with live code mounting
docker run -p 5000:5000 \
  -v ./app_container.py:/app/app_container.py \
  -v ./templates:/app/templates \
  -v ./static:/app/static \
  soundboard-dev
```

### Viewing Container Internals
```bash
# Execute bash in running container
docker exec -it soundboard-app_2-soundboard-1 bash

# Check file structure
docker exec soundboard-app_2-soundboard-1 ls -la /app/
```

## Performance Notes

- **Container size**: ~150MB (Python 3.11 slim + Flask)
- **Memory usage**: ~50MB runtime
- **Audio latency**: Browser-dependent (typically <100ms)
- **Concurrent users**: Flask development server (single-threaded)

## Production Deployment

For production use, consider:

1. **Use a WSGI server** like Gunicorn:
   ```dockerfile
   CMD ["gunicorn", "--bind", "0.0.0.0:5000", "app_container:app"]
   ```

2. **Add nginx reverse proxy** for better performance

3. **Use Docker swarm or Kubernetes** for scaling

4. **Add proper logging and monitoring**

## Comparison with Original Version

✅ **Advantages**:
- Universal Docker compatibility
- No system audio driver dependencies  
- Easy deployment and distribution
- Consistent behavior across platforms

⚠️ **Limitations**:
- Hotkeys only work when browser tab is focused
- Requires manual audio initialization in browser
- Slightly higher audio latency than native playback

The containerized version is perfect for:
- **Remote deployment**
- **Multiple environments** 
- **Sharing the app** with others
- **Cloud hosting**
- **Development consistency**
