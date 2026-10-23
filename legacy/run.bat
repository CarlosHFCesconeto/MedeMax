@echo off
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo Criando ambiente virtual...
    python -m venv .venv
)

call ".venv\Scripts\activate.bat"

echo Instalando/atualizando dependencias...
python -m pip install --upgrade pip
pip install -r requirements.txt

echo.
echo Iniciando Monitor Modbus RTU...
python main.py

pause
