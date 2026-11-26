# TeamSync

Plataforma para que los equipos de proyectos escolares acuerden, registren y validen
la contribución de cada integrante. Cada persona tiene una **parte justa** del trabajo
de cada fase, su aporte se **valida entre pares** y, al concluir, el equipo firma una
**declaración de contribución**.

- **Servidor:** FastAPI + SQLModel (SQLite), autenticación con JWT.
- **Cliente:** Angular 20 (componentes standalone y signals).
- **Metodología:** XP, en dos iteraciones.

## Funcionalidades

| Historia | Qué hace |
|---|---|
| 1. Cuenta y sesión | Registro e inicio de sesión con JWT (expira en 60 min). |
| 2. Proyectos e invitaciones | El líder crea el proyecto e invita por correo; la persona acepta o rechaza. |
| 3. Puntos acordados | El líder propone los puntos de una actividad y cuenta como su voto. El equipo vota y se usa la **mediana**: se acuerda en automático cuando votan todos, o el líder cierra la votación cuando votó la mayoría. |
| 4. Avances | El responsable registra su avance con evidencia. Solo puede tener un avance pendiente a la vez, y no puede registrar avances si la actividad ya está completada o sigue en votación. |
| 5. Revisión | El líder aprueba o rechaza los avances; para rechazar tiene que escribir un comentario. **El líder no aprueba sus propios avances**: los revisa otro integrante. |
| 6. Check-in entre pares | Al cierre de la fase, cada integrante evalúa a sus compañeros en comunicación, calidad y compromiso (1 a 5) y confirma si sus avances aprobados reflejan lo que realmente aportaron. |
| 7. Contribución vs. parte justa | Parte justa = puntos acordados de la fase ÷ integrantes. Puntos validados = puntos aprobados que confirmó la mayoría de los pares. Cumplimiento = validados ÷ parte justa. La fase solo se cierra si todos alcanzan el mínimo y terminaron su check-in. Cada integrante recibe un aviso privado y el líder ve al equipo completo. |
| 8. Declaración y firma | Cuando el líder concluye el proyecto, se genera la declaración con los puntos y el porcentaje de cada persona. **Sin aporte validado no hay firma.** |
| Administrador | Gestiona usuarios (activar, desactivar y dar rol de admin), configura los parámetros (porcentaje mínimo y días de inactividad) y consulta reportes por proyecto. |

## Requisitos

- Python 3.11 o superior
- Node.js 20 o superior y npm

## Instalación y ejecución

### 1. Servidor (terminal 1)

```bash
cd server
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload      # siempre desde la carpeta server/
```

La API queda en `http://127.0.0.1:8000` y la documentación interactiva en
`http://127.0.0.1:8000/docs`.

### 2. Cliente (terminal 2)

```bash
cd client
npm install
npm start                          # o: npx ng serve
```

Abre `http://localhost:4200`. El servidor solo acepta peticiones (CORS) desde ese origen.

### 3. Pruebas

```bash
cd server && python3 -m pytest     # pruebas de la API
cd client && npx ng test --watch=false
```

## Variables de entorno (opcionales)

| Variable | Valor por defecto | Para qué sirve |
|---|---|---|
| `TEAMSYNC_SECRET_KEY` | clave de desarrollo | Firma los JWT. **Cámbiala fuera de tu máquina.** |
| `TEAMSYNC_ADMIN_EMAILS` | `admin@teamsync.local` | Correos (separados por coma) que obtienen el rol de administrador al registrarse. |
| `DATABASE_URL` | `sqlite:///./teamsync.db` | Base de datos. |

Para tener un administrador, registra una cuenta con `admin@teamsync.local` (o con el
correo que pongas en `TEAMSYNC_ADMIN_EMAILS`). Desde su panel puede dar el rol a otras personas.

## Nota sobre la base de datos

Las tablas se crean al iniciar el servidor (`create_all`) y no hay migraciones. **Si cambian
los modelos, borra `server/teamsync.db`** antes de volver a iniciar el servidor; en desarrollo
se pierden los datos de prueba.

## Flujo de una fase

1. El líder crea las actividades y propone los puntos de cada una; el equipo vota.
2. Cada responsable registra sus avances y el revisor los aprueba o los rechaza con un comentario.
3. En **Contribuciones / Cierre de fase**, cada quien hace su check-in de sus compañeros.
4. Si todos alcanzan el mínimo de su parte justa, el líder cierra la fase (lo que no se
   terminó pasa a la siguiente) o concluye el proyecto.
5. Cada integrante con aporte validado firma la declaración de contribución.

## Estructura

```
server/app/
  models.py        tablas (SQLModel)
  schemas.py       entradas y salidas de la API
  reglas.py        parte justa, validación por pares y cierre de fase
  routers/         auth, proyectos, actividades, fases, admin
server/tests/      pruebas de las iteraciones 1 y 2
client/src/app/
  core/            servicios, modelos, guards e interceptor
  features/        landing, auth, dashboard, projects, admin
```
