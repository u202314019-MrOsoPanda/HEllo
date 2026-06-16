@echo off
cd /d "%~dp0"
echo.
echo  SmartRoute WMS - App Web (Flask + HTML)
echo.

set "PY="
where py >nul 2>&1 && set "PY=py -3"
if not defined PY where python >nul 2>&1 && set "PY=python"

if not defined PY (
    echo [ERROR] No se encontro Python. Instale desde https://www.python.org/downloads/
    pause
    exit /b 1
)

if not defined PORT set "PORT=5000"

echo  Cerrando servidores viejos en puerto %PORT%...
for /f "tokens=5" %%i in ('netstat -ano ^| findstr ":%PORT%" ^| findstr LISTENING') do (
    taskkill /F /PID %%i >nul 2>&1
)

echo  Instalando dependencias...
%PY% -m pip install -r requirements.txt -q

echo  Iniciando en http://127.0.0.1:%PORT%
set "PORT=%PORT%"
echo.
%PY% main.py
pause
