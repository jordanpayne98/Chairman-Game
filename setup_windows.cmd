@echo off
setlocal
cd /d "%~dp0"
py -3.12 -m venv .venv
if errorlevel 1 goto failed
.venv\Scripts\python.exe -m pip install -r requirements.txt
if errorlevel 1 goto failed
.venv\Scripts\python.exe tools\check_environment.py
if errorlevel 1 goto failed
echo Environment check passed. This is a development setup, not a playable game.
pause
exit /b 0
:failed
echo Setup failed. Keep this window open and share the error shown above.
pause
exit /b 1
