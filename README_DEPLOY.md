# Guía rápida de despliegue en la nube

## Estructura recomendada

- Frontend React/Vite: Vercel o Render Static Site.
- Backend FastAPI: Render/Railway como servicio Docker.
- Base de datos: PostgreSQL administrado en Render/Railway/Neon/Supabase.
- Futuro agente de IA: crear un segundo servicio tipo worker, conectado a la misma base de datos y, si hace falta, a Redis.

## Cambios incluidos en esta versión cloud_ready

1. Se eliminaron `.env`, `.git`, `.venv`, `node_modules`, `__pycache__` y archivos `.pyc` del ZIP limpio.
2. El backend ahora usa el puerto dinámico `${PORT:-8000}`.
3. CORS ahora lee `CORS_ORIGINS` desde variables de entorno.
4. El callback del frontend para Microsoft ahora es configurable con `FRONTEND_CALLBACK_URL`.
5. Se agregaron `.env.example` para backend y frontend.
6. Se agregaron `.dockerignore` para evitar subir archivos pesados o privados.

## Variables mínimas del backend

```env
APP_ENV=production
APP_DEBUG=false
DATABASE_URL=postgresql+psycopg://USER:PASSWORD@HOST:PORT/DBNAME
CORS_ORIGINS=https://TU-FRONTEND.vercel.app
JWT_SECRET_KEY=clave-larga-segura
MICROSOFT_CLIENT_ID=...
MICROSOFT_CLIENT_SECRET=...
MICROSOFT_TENANT_ID=common
MICROSOFT_REDIRECT_URI=https://TU-BACKEND.onrender.com/api/v1/microsoft/callback
MICROSOFT_SCOPES=openid profile offline_access User.Read Mail.Read
FRONTEND_CALLBACK_URL=https://TU-FRONTEND.vercel.app/microsoft/callback
```

## Variable mínima del frontend

```env
VITE_API_URL=https://TU-BACKEND.onrender.com/api/v1
```

## Render + Vercel

### Backend en Render

1. Sube este proyecto limpio a GitHub.
2. Crea un servicio PostgreSQL administrado.
3. Crea un Web Service para `backend_base` usando Docker.
4. Agrega las variables del backend.
5. Verifica que `/docs` y `/api/v1/health` respondan.

### Frontend en Vercel

1. Crea un proyecto desde el mismo repositorio.
2. Root Directory: `correo-frontend`.
3. Build Command: `npm run build`.
4. Output Directory: `dist`.
5. Environment Variable: `VITE_API_URL=https://TU-BACKEND.../api/v1`.

### Microsoft Entra

Agrega este Redirect URI en la app registrada:

```txt
https://TU-BACKEND.onrender.com/api/v1/microsoft/callback
```

Y deja el callback del frontend así en el backend:

```env
FRONTEND_CALLBACK_URL=https://TU-FRONTEND.vercel.app/microsoft/callback
```

## Futuro agente de IA

No lo metas dentro del frontend. Lo más sano es agregarlo como:

- Endpoint en FastAPI para acciones pequeñas: resumen, explicación, priorización.
- Worker separado para tareas pesadas: leer correos, resumir lotes, detectar importantes, generar respuestas sugeridas.
- Tabla nueva de auditoría para registrar acciones del agente.
- Permisos claros antes de acciones sensibles como eliminar correos.

Tablas futuras sugeridas:

- `agent_tasks`: tareas pendientes y estado.
- `agent_logs`: decisiones tomadas por el agente.
- `email_summaries`: resumen, prioridad y etiquetas inteligentes.
- `agent_permissions`: qué acciones puede hacer cada rol.

## Seguridad antes de producción

- No subir `.env` a GitHub.
- Cambiar/rotar secretos si alguna vez se subieron.
- Cambiar `DEFAULT_ADMIN_PASSWORD`.
- Usar HTTPS en backend y frontend.
- Guardar tokens Microsoft cifrados si el proyecto va a usarse con usuarios reales.
