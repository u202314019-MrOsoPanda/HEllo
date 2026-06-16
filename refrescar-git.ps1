# Refrescar PATH para que reconozca Git (sin cerrar la ventana)
$env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")
git --version
