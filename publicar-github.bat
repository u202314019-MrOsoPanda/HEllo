@echo off
chcp 65001 >nul
setlocal

set "GIT=C:\Program Files\Git\cmd\git.exe"
set "GH=gh"
set "REPO=smartroute-wms"

cd /d "%~dp0"

where gh >nul 2>&1
if errorlevel 1 (
    echo [ERROR] GitHub CLI no encontrado. Instale con: winget install GitHub.cli
    pause
    exit /b 1
)

if not exist "%GIT%" (
    echo [ERROR] Git no encontrado.
    pause
    exit /b 1
)

gh auth status >nul 2>&1
if errorlevel 1 (
    echo.
    echo === Inicie sesion en GitHub ===
    echo Se abrira el navegador o le dara un codigo en https://github.com/login/device
    echo.
    gh auth login -h github.com -p https -w
    if errorlevel 1 (
        echo [ERROR] No se pudo iniciar sesion.
        pause
        exit /b 1
    )
)

if not exist ".git" (
    echo Inicializando repositorio...
    "%GIT%" init
    "%GIT%" add .
    "%GIT%" commit -m "SmartRoute WMS - TB2 Complejidad Algoritmica UPC"
)

"%GIT%" branch -M main

echo.
echo Creando repositorio publico "%REPO%" y subiendo codigo...
gh repo create %REPO% --public --source=. --remote=origin --push

if errorlevel 1 (
    echo.
    echo Si el nombre ya existe, cambie REPO en este archivo o use:
    echo   gh repo create OTRO-NOMBRE --public --source=. --remote=origin --push
    pause
    exit /b 1
)

echo.
echo === Publicado ===
gh repo view --web
pause
