@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo 正在安裝 Qt WebEngine，第一次可能需要數分鐘...
python -m venv "%LOCALAPPDATA%\local-browser-venv"
if errorlevel 1 goto fail
"%LOCALAPPDATA%\local-browser-venv\Scripts\python.exe" -m pip install --upgrade pip
"%LOCALAPPDATA%\local-browser-venv\Scripts\python.exe" -m pip install -r "%~dp0requirements.txt"
if errorlevel 1 goto fail
echo 安裝完成。請執行「啟動瀏覽器.bat」。
pause
exit /b 0
:fail
echo 安裝失敗。請確認已安裝 Python 3.12，而且 python 指令可用。
pause
exit /b 1
