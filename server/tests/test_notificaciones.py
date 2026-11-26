from fastapi.testclient import TestClient

from test_iteracion1 import client, test_engine  # noqa: F401 (fixtures)
from test_iteracion2 import actividad, completar, equipo, evaluar, votar_todos


def avisos(client: TestClient, headers) -> dict:
    respuesta = client.get("/notificaciones", headers=headers)
    assert respuesta.status_code == 200
    return respuesta.json()


def titulos(client: TestClient, headers) -> list[str]:
    return [n["titulo"] for n in avisos(client, headers)["notificaciones"]]


def test_invitacion_y_union_al_equipo(client: TestClient):
    proyecto_id, usuarios, headers = equipo(client, "Lider", "Ana")
    # Ana recibió la invitación; el líder supo que se unió.
    assert "Te invitaron a «Proyecto»" in titulos(client, headers[1])
    assert "Ana se unió a «Proyecto»" in titulos(client, headers[0])
    invitacion = next(n for n in avisos(client, headers[1])["notificaciones"] if n["tipo"] == "invitacion")
    assert invitacion["enlace"] == "/dashboard"


def test_eventos_del_flujo_de_trabajo(client: TestClient):
    proyecto_id, usuarios, headers = equipo(client, "Lider", "Ana")
    lider, ana = usuarios
    act = actividad(client, proyecto_id, headers[0], ana["id"], 4, "Maqueta")
    assert "Vota los puntos de «Maqueta»" in titulos(client, headers[1])

    votar_todos(client, act, headers, 4)
    assert "Ya pueden trabajar en «Maqueta»" in titulos(client, headers[1])

    avance = client.post(f"/actividades/{act}/avances", json={"descripcion": "Hecha"}, headers=headers[1]).json()
    assert "Revisa el avance de Ana" in titulos(client, headers[0])

    client.patch(f"/avances/{avance['id']}/revisar", json={"estado": "aprobado"}, headers=headers[0])
    ana_avisos = titulos(client, headers[1])
    assert "Aprobaron tu avance en «Maqueta»" in ana_avisos
    assert "Ya puedes hacer tu check-in de la fase 1" in ana_avisos

    # El avance del líder lo revisa otro integrante: a ella le llega el aviso.
    propia = actividad(client, proyecto_id, headers[0], lider["id"], 2, "Guion")
    votar_todos(client, propia, headers, 2)
    client.post(f"/actividades/{propia}/avances", json={"descripcion": "Listo"}, headers=headers[0])
    assert "Revisa el avance de Lider" in titulos(client, headers[1])


def test_rechazo_incluye_el_comentario(client: TestClient):
    proyecto_id, usuarios, headers = equipo(client, "Lider", "Ana")
    act = actividad(client, proyecto_id, headers[0], usuarios[1]["id"], 3, "Póster")
    votar_todos(client, act, headers, 3)
    avance = client.post(f"/actividades/{act}/avances", json={"descripcion": "v1"}, headers=headers[1]).json()
    client.patch(
        f"/avances/{avance['id']}/revisar",
        json={"estado": "rechazado", "comentario": "Falta la bibliografía"},
        headers=headers[0],
    )
    rechazo = next(n for n in avisos(client, headers[1])["notificaciones"] if n["tipo"] == "resultado")
    assert rechazo["titulo"] == "Rechazaron tu avance en «Póster»"
    assert "Falta la bibliografía" in rechazo["mensaje"]


def test_recordatorios_una_vez_al_dia(client: TestClient):
    proyecto_id, usuarios, headers = equipo(client, "Lider", "Ana")
    lider, ana = usuarios
    act = actividad(client, proyecto_id, headers[0], ana["id"], 4, "Encuesta")
    votar_todos(client, act, headers, 4)

    # Ana tiene una actividad sin avance: recordatorio, y solo uno aunque consulte varias veces.
    for _ in range(3):
        datos = avisos(client, headers[1])
    recordatorios = [n for n in datos["notificaciones"] if n["titulo"] == "No olvides enviar tu avance"]
    assert len(recordatorios) == 1
    assert recordatorios[0]["mensaje"] == "Tienes 1 actividad sin avance en «Proyecto»: Encuesta."

    # Con el check-in abierto, recuerda calificar a los compañeros...
    otra = actividad(client, proyecto_id, headers[0], lider["id"], 4, "Informe")
    votar_todos(client, otra, headers, 4)
    completar(client, otra, headers[0], headers[1])
    assert titulos(client, headers[1]).count("No olvides calificar a tus compañeros") == 1
    # ...pero no a quien ya evaluó a todos.
    evaluar(client, proyecto_id, headers[0], ana["id"])
    assert "No olvides calificar a tus compañeros" not in titulos(client, headers[0])


def test_leer_y_privacidad(client: TestClient):
    proyecto_id, usuarios, headers = equipo(client, "Lider", "Ana")
    datos = avisos(client, headers[1])
    assert datos["no_leidas"] >= 1
    primera = datos["notificaciones"][0]

    # Nadie más puede marcar mis notificaciones.
    assert client.post(f"/notificaciones/{primera['id']}/leer", headers=headers[0]).status_code == 404
    leida = client.post(f"/notificaciones/{primera['id']}/leer", headers=headers[1])
    assert leida.status_code == 200 and leida.json()["leida"] is True

    todas = client.post("/notificaciones/leer-todas", headers=headers[1]).json()
    assert todas["no_leidas"] == 0
    assert client.get("/notificaciones").status_code == 401
