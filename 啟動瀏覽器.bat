@echo off
chcp 65001 >nul
cd /d "%~dp0"
set "PYW=%LOCALAPPDATA%\local-browser-venv\Scripts\pythonw.exe"
if not exist "%PYW%" set "PYW=%LOCALAPPDATA%\local-browser-venv\Scripts\python.exe"
if not exist "%PYW%" (
  echo 尚未安裝。請先執行「安裝.bat」。
  pause
  exit /b 1
)
start "" "%PYW%" "%~dp0main.py"
