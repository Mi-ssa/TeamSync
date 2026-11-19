import pytest
from fastapi.testclient import TestClient
from sqlmodel import SQLModel, Session, create_engine, select
from sqlalchemy.pool import StaticPool

from app.database import get_session
from app.main import app
from app.models import Participacion


@pytest.fixture
def test_engine():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    yield engine
    SQLModel.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture
def client(test_engine):
    def get_test_session():
        with Session(test_engine) as session:
            yield session

    app.dependency_overrides[get_session] = get_test_session
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def register(client: TestClient, nombre: str, correo: str) -> dict[str, str]:
    response = client.post(
        "/auth/register",
        json={"nombre": nombre, "correo": correo, "contrasena": "contrasena-segura"},
    )
    assert response.status_code == 201
    return response.json()


def login(client: TestClient, correo: str) -> dict[str, str]:
    response = client.post(
        "/auth/login",
        json={"correo": correo, "contrasena": "contrasena-segura"},
    )
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def test_register_login_and_current_profile(client: TestClient):
    register(client, "Líder", "lider@example.com")
    headers = login(client, "lider@example.com")

    response = client.get("/auth/me", headers=headers)
    assert response.status_code == 200
    assert response.json()["correo"] == "lider@example.com"


def test_project_invitation_and_access_requires_acceptance(client: TestClient, test_engine):
    lider = register(client, "Líder", "lider@example.com")
    integrante = register(client, "Integrante", "integrante@example.com")
    leader_headers = login(client, "lider@example.com")
    member_headers = login(client, "integrante@example.com")

    project_response = client.post(
        "/proyectos",
        json={"nombre": "Proyecto de prueba", "descripcion": "Iteración 1"},
        headers=leader_headers,
    )
    assert project_response.status_code == 201
    proyecto_id = project_response.json()["id"]
    assert project_response.json()["creado_por_id"] == lider["id"]
    with Session(test_engine) as session:
        lider_participation = session.exec(
            select(Participacion).where(
                Participacion.proyecto_id == proyecto_id,
                Participacion.usuario_id == lider["id"],
            )
        ).one()
        assert lider_participation.rol == "lider"
        assert lider_participation.estado == "aceptada"

    invitation_response = client.post(
        f"/proyectos/{proyecto_id}/invitaciones",
        json={"correo": integrante["correo"]},
        headers=leader_headers,
    )
    assert invitation_response.status_code == 201
    assert invitation_response.json()["estado"] == "pendiente"
    invitation_id = invitation_response.json()["id"]

    assert client.get(f"/proyectos/{proyecto_id}", headers=member_headers).status_code == 403
    listing = client.get("/proyectos", headers=member_headers).json()
    assert len(listing["invitaciones_pendientes"]) == 1

    response = client.post(
        f"/invitaciones/{invitation_id}/responder",
        json={"respuesta": "aceptar"},
        headers=member_headers,
    )
    assert response.status_code == 200
    assert response.json()["estado"] == "aceptada"
    assert client.get(f"/proyectos/{proyecto_id}", headers=member_headers).status_code == 200
    members = client.get(f"/proyectos/{proyecto_id}/integrantes", headers=member_headers)
    assert members.status_code == 200
    assert {member["id"] for member in members.json()} == {lider["id"], integrante["id"]}


def test_activity_progress_and_leader_approval(client: TestClient):
    leader = register(client, "Líder", "lider@example.com")
    member = register(client, "Integrante", "integrante@example.com")
    leader_headers = login(client, "lider@example.com")
    member_headers = login(client, "integrante@example.com")
    project_id = client.post(
        "/proyectos",
        json={"nombre": "Proyecto"},
        headers=leader_headers,
    ).json()["id"]
    invitation = client.post(
        f"/proyectos/{project_id}/invitaciones",
        json={"correo": member["correo"]},
        headers=leader_headers,
    ).json()
    client.post(
        f"/invitaciones/{invitation['id']}/responder",
        json={"respuesta": "aceptar"},
        headers=member_headers,
    )

    activity_response = client.post(
        f"/proyectos/{project_id}/actividades",
        json={
            "nombre": "Diseñar prototipo",
            "descripcion": "Crear primera versión",
            "puntos_acordados": 5,
            "responsable_id": member["id"],
        },
        headers=leader_headers,
    )
    assert activity_response.status_code == 201
    assert activity_response.json()["estado"] == "pendiente"
    activity_id = activity_response.json()["id"]

    listed = client.get(f"/proyectos/{project_id}/actividades", headers=leader_headers)
    assert listed.status_code == 200
    assert len(listed.json()) == 1

    progress_response = client.post(
        f"/actividades/{activity_id}/avances",
        json={"descripcion": "Prototipo terminado", "url_evidencia": "https://example.com/evidencia"},
        headers=member_headers,
    )
    assert progress_response.status_code == 201
    assert progress_response.json()["estado"] == "pendiente"
    progress_id = progress_response.json()["id"]
    advances = client.get(f"/actividades/{activity_id}/avances", headers=leader_headers)
    assert advances.status_code == 200
    assert advances.json()[0]["id"] == progress_id

    review_response = client.patch(
        f"/avances/{progress_id}/revisar",
        json={"estado": "aprobado"},
        headers=leader_headers,
    )
    assert review_response.status_code == 200
    assert review_response.json()["estado"] == "aprobado"
    assert client.get(f"/proyectos/{project_id}/actividades", headers=leader_headers).json()[0]["estado"] == "completada"


def test_rechazar_avance_requiere_comentario(client: TestClient):
    member = register(client, "Integrante", "integrante@example.com")
    register(client, "Líder", "lider@example.com")
    leader_headers = login(client, "lider@example.com")
    member_headers = login(client, "integrante@example.com")
    project_id = client.post("/proyectos", json={"nombre": "Proyecto"}, headers=leader_headers).json()["id"]
    invitation = client.post(
        f"/proyectos/{project_id}/invitaciones",
        json={"correo": member["correo"]},
        headers=leader_headers,
    ).json()
    client.post(
        f"/invitaciones/{invitation['id']}/responder",
        json={"respuesta": "aceptar"},
        headers=member_headers,
    )
    activity_id = client.post(
        f"/proyectos/{project_id}/actividades",
        json={"nombre": "Diseñar prototipo", "puntos_acordados": 5, "responsable_id": member["id"]},
        headers=leader_headers,
    ).json()["id"]
    progress_id = client.post(
        f"/actividades/{activity_id}/avances",
        json={"descripcion": "Prototipo terminado"},
        headers=member_headers,
    ).json()["id"]

    sin_comentario = client.patch(
        f"/avances/{progress_id}/revisar",
        json={"estado": "rechazado", "comentario": "   "},
        headers=leader_headers,
    )
    assert sin_comentario.status_code == 400

    rechazo = client.patch(
        f"/avances/{progress_id}/revisar",
        json={"estado": "rechazado", "comentario": "Falta la pantalla de inicio"},
        headers=leader_headers,
    )
    assert rechazo.status_code == 200
    assert rechazo.json()["estado"] == "rechazado"
    assert rechazo.json()["comentario_revision"] == "Falta la pantalla de inicio"
    actividad = client.get(f"/proyectos/{project_id}/actividades", headers=leader_headers).json()[0]
    assert actividad["estado"] == "pendiente"
