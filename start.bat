@echo off
cd /d "%~dp0"
echo.
echo  Locks Manager — PHA Hotel
echo  =============================
echo  Abriendo en http://localhost:5000
echo.
start http://localhost:5000
python app.py
pause
