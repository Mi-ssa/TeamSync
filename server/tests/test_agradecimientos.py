import pytest
from fastapi.testclient import TestClient

from app.agradecimientos import motivo_mensaje_insuficiente
from test_iteracion1 import client, test_engine  # noqa: F401 (fixtures)
from test_iteracion2 import actividad, equipo, votar_todos


@pytest.mark.parametrize(
    "mensaje",
    ["gracias", "¡Gracias!!", "Muchas gracias de verdad", "gracias, buen trabajo, excelente", "Gracias por todo crack"],
)
def test_un_gracias_generico_no_basta(mensaje):
    assert motivo_mensaje_insuficiente(mensaje) is not None


@pytest.mark.parametrize(
    "mensaje",
    [
        "Gracias por el prototipo, nos ahorró una semana",
        "Tus pruebas encontraron el error del login antes de la entrega",
        "Excelente trabajo con las referencias en formato IEEE",
    ],
)
def test_un_gracias_concreto_si(mensaje):
    assert motivo_mensaje_insuficiente(mensaje) is None


def avance_aprobado(client, proyecto_id, headers, responsable, autor_headers):
    act = actividad(client, proyecto_id, headers[0], responsable["id"], 3, "Prototipo")
    votar_todos(client, act, headers, 3)
    avance = client.post(f"/actividades/{act}/avances", json={"descripcion": "Listo"}, headers=autor_headers).json()
    return act, avance


def test_agradecer_un_avance_aprobado(client: TestClient):
    proyecto_id, (lider, ana, beto), headers = equipo(client, "Lider", "Ana", "Beto")
    act, avance = avance_aprobado(client, proyecto_id, headers, ana, headers[1])
    url = f"/avances/{avance['id']}/agradecimientos"
    mensaje = "Tu prototipo dejó claras las pantallas y avanzamos rápido"

    # Todavía no está aprobado.
    assert client.post(url, json={"mensaje": mensaje}, headers=headers[2]).status_code == 409
    client.patch(f"/avances/{avance['id']}/revisar", json={"estado": "aprobado"}, headers=headers[0])

    # Un gracias genérico se rechaza con una explicación.
    generico = client.post(url, json={"mensaje": "¡Muchas gracias!"}, headers=headers[2])
    assert generico.status_code == 400
    assert "algo concreto que hizo" in generico.json()["detail"]
    # Nadie se agradece a sí mismo.
    assert client.post(url, json={"mensaje": mensaje}, headers=headers[1]).status_code == 403

    respuesta = client.post(url, json={"mensaje": mensaje}, headers=headers[2])
    assert respuesta.status_code == 201
    gracias = respuesta.json()["agradecimientos"]
    assert len(gracias) == 1 and gracias[0]["de_nombre"] == "Beto" and gracias[0]["mensaje"] == mensaje
    # Una vez por persona y avance.
    assert client.post(url, json={"mensaje": mensaje + " otra vez"}, headers=headers[2]).status_code == 409

    # Se ve en el avance para el equipo y le llega a Ana como notificación.
    listado = client.get(f"/actividades/{act}/avances", headers=headers[0]).json()
    assert listado[0]["agradecimientos"][0]["de_nombre"] == "Beto"
    avisos = client.get("/notificaciones", headers=headers[1]).json()["notificaciones"]
    aviso = next(n for n in avisos if n["tipo"] == "agradecimiento")
    assert aviso["titulo"] == "Beto te agradeció tu trabajo en «Prototipo»" and aviso["mensaje"] == mensaje


def test_no_cuenta_para_la_contribucion(client: TestClient):
    proyecto_id, (lider, ana, beto), headers = equipo(client, "Lider", "Ana", "Beto")
    act, avance = avance_aprobado(client, proyecto_id, headers, ana, headers[1])
    client.patch(f"/avances/{avance['id']}/revisar", json={"estado": "aprobado"}, headers=headers[0])
    antes = client.get(f"/proyectos/{proyecto_id}/contribucion", headers=headers[0]).json()
    client.post(
        f"/avances/{avance['id']}/agradecimientos",
        json={"mensaje": "Gracias por resolver el diseño de la portada a tiempo"},
        headers=headers[2],
    )
    despues = client.get(f"/proyectos/{proyecto_id}/contribucion", headers=headers[0]).json()
    assert antes["integrantes"] == despues["integrantes"]
