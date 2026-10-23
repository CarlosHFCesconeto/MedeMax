@echo off
cd /d "%~dp0"
python -m pip install -r requirements-dev.txt
if errorlevel 1 goto fail
python -m PyInstaller --noconfirm --clean --windowed --onefile --name MonitorModbus --collect-all pyqtgraph --add-data "assets;assets" main.py
if errorlevel 1 goto fail
echo Executavel: dist\MonitorModbus.exe
pause
exit /b 0
:fail
echo Nao foi possivel gerar o executavel.
pause
exit /b 1
