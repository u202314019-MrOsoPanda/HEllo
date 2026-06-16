@echo off
REM Usa Git aunque PowerShell no tenga el PATH actualizado
set "GIT=C:\Program Files\Git\cmd\git.exe"

if not exist "%GIT%" (
    echo [ERROR] Git no encontrado. Instale desde https://git-scm.com/download/win
    echo O ejecute en PowerShell: winget install Git.Git
    pause
    exit /b 1
)

"%GIT%" --version
echo.

cd /d "%~dp0"

if not exist ".git" (
    echo Inicializando repositorio...
    "%GIT%" init
)

echo.
echo Agregando archivos...
"%GIT%" add .

echo.
"%GIT%" status
echo.
set /p MSG=Mensaje del commit [SmartRoute WMS TB2]: 
if "%MSG%"=="" set "MSG=SmartRoute WMS TB2"

"%GIT%" commit -m "%MSG%"
if errorlevel 1 (
    echo.
    echo Si pide nombre/email, ejecute:
    echo   "%GIT%" config user.email "tu@email.com"
    echo   "%GIT%" config user.name "Tu Nombre"
    pause
    exit /b 1
)

echo.
echo === Commit local listo ===
echo.
echo Para crear el repo en GitHub y subir todo automaticamente, ejecute:
echo    publicar-github.bat
echo.
echo (Requiere GitHub CLI: winget install GitHub.cli y sesion con gh auth login)
echo.
echo Despliegue web: https://render.com - Root Directory: APP hecha
echo Ver APP hecha\DEPLOY.md
echo.
pause
