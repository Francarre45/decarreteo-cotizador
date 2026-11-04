# Cotizador DeCarreteo.com

App interna para que el equipo genere cotizaciones/itinerarios en PDF con el diseño de marca de DeCarreteo, sin pasar por Claude.

## Qué incluye
- Login propio (email + contraseña).
- 3 formularios: hotel único, multi-hotel (2-4 opciones), itinerario día a día.
- Generación de PDF idéntica a las plantillas HTML/CSS originales (weasyprint).
- Bloqueo de generación si falta un dato obligatorio (seña, origen, año, etc.) — nunca se inventa.
- Historial de cotizaciones: cada usuario ve solo las suyas, salvo que tenga el permiso "ve todas" (otorgable por el admin en `/admin/usuarios`).

## Admin por defecto
- Email: `fran166carre@gmail.com`
- Contraseña inicial: `decarreteo2026`

**Cambiá esta contraseña apenas entres por primera vez** (desde `/admin/usuarios` no hay botón de cambio de contraseña todavía — por ahora se cambia editando la base de datos o recreando el usuario; es una mejora pendiente).

## Deploy en Render (prueba gratuita)

1. Entrá a [render.com](https://render.com) y creá una cuenta gratis (podés usar "Sign up with GitHub").
2. Click en **New +** → **Blueprint**.
3. Conectá este repositorio (`decarreteo-cotizador`).
4. Render va a detectar el archivo `render.yaml` y proponer el servicio automáticamente. Click en **Apply**.
5. Esperá unos minutos a que haga el build (usa Docker porque WeasyPrint necesita librerías de sistema para generar los PDFs).
6. Cuando termine, te da una URL tipo `https://decarreteo-cotizador.onrender.com`. Esa es la que compartís con tu equipo.

### ⚠️ Importante sobre el plan gratuito de Render
El plan free de Render **no tiene disco persistente**: cada vez que se reinicia o se vuelve a desplegar el servicio (incluido el "sleep" automático por inactividad), se pierden la base de datos (usuarios, historial) y los PDFs generados. Es perfecto para **probar la herramienta ahora**, pero antes de usarla en serio con el equipo hay que:
- Pasar a un plan pago de Render con disco persistente, o
- Migrar la base de datos a un servicio externo (ej. Render Postgres, que sí persiste incluso en el free tier) y los PDFs a un storage externo (ej. S3/Cloudflare R2).

Avisame cuando quieras dar ese paso y lo preparamos.

## Correrlo localmente
```bash
python3 -m venv venv
./venv/bin/pip install -r requirements.txt
./venv/bin/python app.py
```
Abrí `http://localhost:5000`.
