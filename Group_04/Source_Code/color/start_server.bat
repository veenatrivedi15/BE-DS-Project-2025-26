@echo off
echo Starting iCare Test Server...
echo.
echo Open http://localhost:8000/test.html in your browser
echo The Export Responses button will save directly to responses.csv
echo.
cd /d "%~dp0"
python web/server.py
pause







