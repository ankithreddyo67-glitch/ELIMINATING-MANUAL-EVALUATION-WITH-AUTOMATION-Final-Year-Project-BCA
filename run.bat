@echo off
setlocal
cd /d "%~dp0"

python --version >nul 2>nul
if not errorlevel 1 goto system_python

if exist "C:\Program Files\Thonny\python.exe" goto thonny_python

echo Python 3.10+ not found in PATH or default locations.
pause
exit /b 1

:system_python
python app.py
exit /b %errorlevel%

:thonny_python
"C:\Program Files\Thonny\python.exe" app.py
exit /b %errorlevel%
