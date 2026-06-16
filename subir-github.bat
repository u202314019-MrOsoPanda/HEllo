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
echo === Listo ===
echo.
echo 1. Cree un repo en https://github.com/new  (vacio, sin README)
echo 2. Luego ejecute (cambie TU_USUARIO y TU-REPO):
echo.
echo    "%GIT%" remote add origin https://github.com/TU_USUARIO/TU-REPO.git
echo    "%GIT%" branch -M main
echo    "%GIT%" push -u origin main
echo.
echo 3. Despliegue en https://render.com - Root Directory: APP hecha
echo    Ver APP hecha\DEPLOY.md
echo.
pause
