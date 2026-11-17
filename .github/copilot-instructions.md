# Contexto del Proyecto: TeamSync

TeamSync es una aplicación web para equipos escolares basada en contribución validada para reducir el *free riding*.

## Arquitectura (3 capas)
- **Frontend (`client/`)**: Angular 20 (SPA, zoneless, standalone components, Signals, `HttpClient`, estilos CSS). Se comunica vía API REST con el servidor.
- **Backend (`server/`)**: FastAPI (Python 3.12) con autenticación JWT (`pyjwt`), hash de contraseñas (`pwdlib[argon2]`), validación con Pydantic y pruebas automáticas con `pytest` + `httpx`.
- **Datos (`server/teamsync.db`)**: SQLModel sobre SQLite con las 7 entidades del modelo AMENITIES: `Usuario`, `Proyecto`, `Participacion`, `Actividad`, `Avance`, `EvaluacionPares`, `Contribucion`.

## Roles y Reglas de Negocio (AMENITIES)
- **Líder**: Quien crea un proyecto se convierte automáticamente en su líder. Puede invitar integrantes por correo, registrar/asignar actividades con puntos acordados y aprobar o rechazar avances. Solo puede eliminar a un participante si existe alerta de inactividad del sistema.
- **Integrante**: Puede aceptar/rechazar invitaciones, ver proyectos donde ya aceptó participar, registrar avances con evidencia en sus actividades asignadas y evaluar a sus pares al cierre de fase. Una persona invitada NO puede ver el detalle del proyecto hasta aceptar la invitación.
- **Sistema de medición**: Calcula puntos validados, parte justa y porcentaje de cumplimiento; detecta inactividad.

## Convenciones
- Entorno virtual de Python ubicado en `server/venv`.
- API en español para nombres de campos/modelos de dominio y mensajes de error claros.