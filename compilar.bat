@echo off
cd /d "%~dp0"
echo Iniciando Nodo Capture...
python main.py
if errorlevel 1 (
    echo.
    echo La app termino con un error. Revisa el mensaje de arriba.
    pause
)
