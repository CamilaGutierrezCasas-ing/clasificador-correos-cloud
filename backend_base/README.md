# Backend Fase 3

Incluye autenticación local con roles y clasificación básica de correos usando TF-IDF + Regresión Logística.

## Endpoints nuevos
- POST /api/v1/emails/classify
- GET /api/v1/emails/mine
- GET /api/v1/emails/{email_id}

## Prueba rápida
1. Registra usuario
2. Haz login
3. Autoriza en Swagger
4. Usa /api/v1/emails/classify con un subject y body
5. Revisa /api/v1/emails/mine
