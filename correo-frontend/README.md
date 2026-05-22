# Frontend - Clasificador de Correos con Microsoft Graph

Frontend desarrollado con React + Vite + Tailwind + Axios + React Router.

## Qué incluye

- Autenticación con JWT
- Persistencia de sesión en localStorage
- Axios configurado con interceptor para token Bearer
- Protección de rutas y control por roles (`usuario`, `secretaria`, `admin`)
- Dashboard de usuario con:
  - cuentas Microsoft conectadas
  - botón para conectar cuenta Microsoft
  - desconexión de cuenta
  - listado de correos clasificados
  - formulario de clasificación manual
- Dashboard de secretaria con revisión y formulario preparado para feedback
- Dashboard de administrador con métricas base y estructura para endpoints administrativos futuros
- Vista para finalizar OAuth de Microsoft desde el frontend

## Instalación

```bash
npm install
npm run dev
```

## Variables de entorno

Crea un archivo `.env` con:

```env
VITE_API_URL=http://localhost:8000/api/v1
```

## Importante sobre Microsoft OAuth

Para que la vista `/oauth/microsoft/callback` funcione desde el frontend, el backend debe usar una `MICROSOFT_REDIRECT_URI` que apunte a esa ruta del frontend. Ejemplo:

```env
MICROSOFT_REDIRECT_URI=http://localhost:5173/oauth/microsoft/callback
```

Esa misma URI debe estar registrada también en Azure App Registration.

## Estructura

```text
src/
├── api/
├── components/
├── contexts/
├── hooks/
├── layouts/
├── pages/
├── routes/
└── utils/
```

## Endpoints consumidos hoy

- `POST /auth/login`
- `POST /auth/register`
- `GET /auth/me`
- `GET /microsoft/connect`
- `GET /microsoft/accounts`
- `POST /microsoft/accounts/{id}/disconnect`
- `GET /microsoft/callback`
- `GET /emails/mine`
- `POST /emails/classify`

## Endpoints recomendados para completar el sistema

- `GET /admin/users`
- `GET /admin/stats`
- `GET /admin/classifier-metrics`
- `POST /emails/{id}/feedback`
- `GET /secretaria/review-queue`

## Nota académica

La estructura está pensada para que el frontend se vea organizado, escalable y defendible en un proyecto de grado, separando responsabilidades por capas: API, contexto de autenticación, rutas protegidas, layouts y páginas por rol.
