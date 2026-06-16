# Publicar SmartRoute WMS en internet

## Importante: ¿Netlify?

**Netlify sirve sitios estáticos** (HTML/CSS/JS puro). SmartRoute WMS usa **Flask + Python** (`server.py`, algoritmos, matplotlib).  
**No puedes subir solo la carpeta a Netlify** y esperar que funcione como en tu PC.

| Plataforma | ¿Funciona esta app? |
|------------|---------------------|
| **Render** | Sí (recomendado, plan gratis) |
| **Railway** | Sí |
| **PythonAnywhere** | Sí |
| **Netlify** | No (solo el backend Python) |

Si el profesor pide un enlace público, usa **Render** (abajo). Si más adelante quieres un dominio en Netlify, puedes apuntar el DNS a Render.

---

## Opción recomendada: Render (gratis)

### 1. Subir el proyecto a GitHub

```powershell
cd "C:\Users\Oso\Downloads\README"
git init
git add .
git commit -m "SmartRoute WMS - TB2"
```

Crea un repo en [github.com/new](https://github.com/new) y:

```powershell
git remote add origin https://github.com/TU_USUARIO/smartroute-wms.git
git branch -M main
git push -u origin main
```

### 2. Crear servicio en Render

1. Entra a [render.com](https://render.com) → **Sign up** (con GitHub).
2. **New +** → **Web Service**.
3. Conecta el repositorio.
4. Configuración:
   - **Root Directory:** `APP hecha`
   - **Runtime:** Python 3
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `gunicorn server:app --bind 0.0.0.0:$PORT --workers 1 --threads 4 --timeout 120`
   - **Instance type:** Free
5. **Create Web Service**.

En 3–5 minutos tendrás una URL como:

`https://smartroute-wms.onrender.com`

### 3. Probar

Abre esa URL → **Navegar** → **Calcular ruta**.  
La primera carga en plan gratis puede tardar ~30 s (el servidor “despierta”).

---

## Archivos ya incluidos para Render

- `Procfile` — comando de arranque
- `render.yaml` — despliegue automático (opcional: **New Blueprint** en Render)
- `gunicorn` en `requirements.txt`

---

## Si insistes en Netlify (solo landing)

Puedes poner en Netlify una página estática que redirija a Render:

`public/index.html`:

```html
<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8">
  <meta http-equiv="refresh" content="0; url=https://TU-APP.onrender.com">
  <title>SmartRoute WMS</title>
</head>
<body>
  <p>Redirigiendo a <a href="https://TU-APP.onrender.com">SmartRoute WMS</a>…</p>
</body>
</html>
```

En Netlify: **Add new site** → arrastra la carpeta `public` → Site settings → cambia la URL de destino.

La **app real** sigue en Render.

---

## Variables de entorno (producción)

En Render → **Environment**:

| Variable | Valor |
|----------|--------|
| `FLASK_SECRET_KEY` | (Render puede generarla automáticamente) |
| `PORT` | (Render la asigna sola) |

---

## Problemas frecuentes

- **Build failed: `No such file ... '/APP'`** — la carpeta se llama `APP hecha` (con espacio). En Render deja **Root Directory vacío**; el arranque usa `wsgi.py` en la raíz del repo.
- **Exit status 127** — comando de inicio no encontrado. En Settings borra el **Start Command** personalizado (deja que use el `Procfile`) o pon: `gunicorn wsgi:app --bind 0.0.0.0:$PORT --workers 1 --threads 4 --timeout 120`
- **Python 3.14 en logs** — en Settings → Environment añade `PYTHON_VERSION` = `3.12.3`.
- **502 / timeout:** el plan gratis es lento al inicio; espera y recarga.
- **Ruta /api falla:** verifica que **Root Directory** sea `APP hecha`, no la raíz del repo.
- **No abrir `index.html` local:** siempre usar la URL `https://...` del servidor.
