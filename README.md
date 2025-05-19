# Soundboard App

## Setup and Run Instructions

1. Create a virtual environment and activate it:
```powershell
python -m venv venv
.\venv\Scripts\Activate
```

2. Install dependencies:
```powershell
# Update pip to latest version
python.exe -m pip install --upgrade pip

# Install pygame separately first (this handles potential installation issues)
pip install pygame --pre

# Install remaining requirements
pip install -r requirements.txt
```

3. Run the application:
```powershell
python app.py
```

The app will now be running at http://localhost:5000. You can access the web interface to play different sound clips.

To stop the application, press Ctrl+C in the terminal.
