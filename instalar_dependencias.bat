@echo off
cd /d "%~dp0"
echo Instalando dependencias no Python compartilhado deste computador...
python -m pip install -r requirements.txt
if errorlevel 1 goto fail
echo Dependencias prontas. Abra run.bat para iniciar o MedeMax.
pause
exit /b 0
:fail
echo Nao foi possivel instalar as dependencias. Veja a mensagem acima.
pause
exit /b 1
