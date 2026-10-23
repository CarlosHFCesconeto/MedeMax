@echo off
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo Execute run.bat primeiro para criar o ambiente.
    pause
    exit /b 1
)

call ".venv\Scripts\activate.bat"
pip install pyinstaller

pyinstaller ^
  --noconfirm ^
  --clean ^
  --windowed ^
  --onefile ^
  --name MonitorModbusRTU ^
  --collect-all pyqtgraph ^
  main.py

echo.
echo Executavel criado em dist\MonitorModbusRTU.exe
pause
