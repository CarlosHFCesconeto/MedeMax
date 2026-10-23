@echo off
cd /d "%~dp0"
python main.py %*
if errorlevel 1 goto fail
exit /b 0
:fail
echo Nao foi possivel abrir o MedeMax. Veja a mensagem acima.
echo Se faltarem bibliotecas, execute instalar_dependencias.bat.
pause
exit /b 1
