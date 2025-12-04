# Tech News RSS Slideshow Feed

A beautiful fullscreen slideshow application that displays tech news from multiple RSS feeds. Perfect for displaying on office TVs or monitors.

## Features

- 📰 Aggregates news from multiple popular tech news sources
- 🎨 Beautiful, modern UI with smooth animations
- 🔄 Auto-refreshes feeds every 5 minutes
- 📺 Fullscreen support for TV displays
- ⌨️ Keyboard controls (Arrow keys, Space, F for fullscreen, R for refresh)
- 📱 Responsive design

## Installation

1. **Install Python** (if not already installed)
   - Download from [python.org](https://www.python.org/downloads/)
   - Make sure to check "Add Python to PATH" during installation

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

## Running the Application

### Option 1: Using the startup script (Windows)
Double-click `start.bat` or run it from the command prompt.

### Option 2: Manual start
```bash
python app.py
```

The application will start on `http://localhost:5000`

### Option 3: Network access (for other devices)
The application runs on `0.0.0.0:5000` by default, so it's accessible from other devices on your network:
- On the same PC: `http://localhost:5000`
- From another device: `http://[YOUR_IP_ADDRESS]:5000`

## Usage

1. Open your browser and navigate to `http://localhost:5000`
2. Click the "Fullscreen" button or press `F` to enter fullscreen mode
3. The slideshow will automatically cycle through news items every 10 seconds
4. Use arrow keys or spacebar to manually navigate
5. Press `R` to refresh feeds manually

## Transferring to Another PC

1. Copy the entire project folder to the other Windows PC
2. Install Python on that PC (if not already installed)
3. Open a terminal in the project folder
4. Run: `pip install -r requirements.txt`
5. Run: `python app.py`
6. Open browser to `http://localhost:5000` and press F11 for fullscreen

## Customization

### Change RSS Feeds
Edit the `RSS_FEEDS` list in `app.py` to add or remove news sources.

### Change Slide Duration
Edit the `SLIDE_DURATION` constant in `templates/index.html` (in milliseconds).

### Change Cache Duration
Edit the `cache_duration` in `app.py` (in seconds).

## Included RSS Feeds

- O'Reilly Radar
- Wired
- TechCrunch
- Ars Technica
- The Verge
- VentureBeat
- Engadget

## Troubleshooting

- **No news loading**: Check your internet connection and firewall settings
- **Port already in use**: Change the port in `app.py` (line 95) from `5000` to another port
- **Feeds not updating**: Check the console for error messages about specific RSS feeds

## License

Free to use and modify for personal or commercial use.

