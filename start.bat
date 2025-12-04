@echo off
echo Starting Tech News RSS Slideshow...
echo.
echo Installing/updating dependencies...
pip install -r requirements.txt
echo.
echo Starting server...
echo Open http://localhost:5000 in your browser
echo Press Ctrl+C to stop the server
echo.
python app.py
pause

