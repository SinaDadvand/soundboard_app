# Soundboard Startup Script with Global Hotkeys
Write-Host "====================================================" -ForegroundColor Cyan
Write-Host "Starting Soundboard with Global Hotkeys" -ForegroundColor Cyan
Write-Host "====================================================" -ForegroundColor Cyan
Write-Host ""

# Check if Docker is running
try {
    docker --version | Out-Null
    Write-Host "✓ Docker is available" -ForegroundColor Green
} catch {
    Write-Host "✗ ERROR: Docker is not running or not installed" -ForegroundColor Red
    Write-Host "Please start Docker Desktop and try again" -ForegroundColor Yellow
    Read-Host "Press Enter to exit"
    exit 1
}

Write-Host "1. Starting containerized soundboard..." -ForegroundColor Yellow
docker-compose up -d

# Wait for container to be ready
Write-Host "2. Waiting for container to start..." -ForegroundColor Yellow
Start-Sleep -Seconds 5

# Check if container is running
$containerStatus = docker-compose ps
if ($containerStatus -match "Up") {
    Write-Host "3. ✓ Container started successfully!" -ForegroundColor Green
} else {
    Write-Host "✗ ERROR: Failed to start soundboard container" -ForegroundColor Red
    Write-Host "Check 'docker-compose logs' for details" -ForegroundColor Yellow
    Read-Host "Press Enter to exit"
    exit 1
}

Write-Host "4. Starting global hotkey client..." -ForegroundColor Yellow
Write-Host ""

# Check if virtual environment exists for hotkey client
if (-not (Test-Path "venv_hotkeys")) {
    Write-Host "Setting up hotkey client environment..." -ForegroundColor Yellow
    python -m venv venv_hotkeys
    & "venv_hotkeys\Scripts\Activate.ps1"
    pip install -r requirements_hotkey_client.txt
} else {
    & "venv_hotkeys\Scripts\Activate.ps1"
}

Write-Host "5. Starting global hotkeys (this window must stay open)..." -ForegroundColor Yellow
Write-Host ""

Write-Host "====================================================" -ForegroundColor Cyan
Write-Host "INSTRUCTIONS:" -ForegroundColor White
Write-Host "- Web interface: http://localhost:5000" -ForegroundColor Green
Write-Host "- Global hotkeys are now active" -ForegroundColor Green
Write-Host "- Keep this window open for hotkeys to work" -ForegroundColor Yellow
Write-Host "- Press Ctrl+C to stop everything" -ForegroundColor Red
Write-Host "====================================================" -ForegroundColor Cyan
Write-Host ""

try {
    python hotkey_client.py
} catch {
    Write-Host "Hotkey client stopped" -ForegroundColor Yellow
} finally {
    # Cleanup when hotkey client exits
    Write-Host ""
    Write-Host "Stopping soundboard container..." -ForegroundColor Yellow
    docker-compose down
    Write-Host "Done!" -ForegroundColor Green
    Read-Host "Press Enter to exit"
}
