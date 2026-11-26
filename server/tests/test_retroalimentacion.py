from fastapi.testclient import TestClient

from test_iteracion1 import client, test_engine  # noqa: F401 (fixtures)
from test_iteracion2 import actividad, completar, equipo, votar_todos


def calificar(client, proyecto_id, headers, evaluado_id, valores, fortaleza=None, mejora=None):
    comunicacion, calidad, compromiso = valores
    respuesta = client.post(
        f"/proyectos/{proyecto_id}/evaluaciones",
        json={
            "evaluado_id": evaluado_id,
            "comunicacion": comunicacion,
            "calidad": calidad,
            "compromiso": compromiso,
            "confirma_aporte": True,
            "fortaleza": fortaleza,
            "mejora": mejora,
        },
        headers=headers,
    )
    assert respuesta.status_code == 201, respuesta.text
    return respuesta.json()


def preparar(client):
    """Equipo de tres; cada quien completa una actividad para abrir el check-in."""
    proyecto_id, usuarios, headers = equipo(client, "Lider", "Ana", "Beto")
    for i, usuario in enumerate(usuarios):
        act = actividad(client, proyecto_id, headers[0], usuario["id"], 4, f"Tarea {i}")
        votar_todos(client, act, headers, 4)
        completar(client, act, headers[i], headers[1] if i == 0 else headers[0])
    return proyecto_id, usuarios, headers


def test_retroalimentacion_anonima_al_cerrar_la_fase(client: TestClient):
    proyecto_id, (lider, ana, beto), headers = preparar(client)
    calificar(client, proyecto_id, headers[0], ana["id"], (5, 4, 5), "Siempre avisó sus avances", "Revisar ortografía")
    calificar(client, proyecto_id, headers[2], ana["id"], (3, 4, 4), "Buen diseño", None)
    calificar(client, proyecto_id, headers[0], beto["id"], (4, 4, 4))
    calificar(client, proyecto_id, headers[1], beto["id"], (4, 4, 4))
    calificar(client, proyecto_id, headers[1], lider["id"], (5, 5, 5))
    calificar(client, proyecto_id, headers[2], lider["id"], (5, 5, 5))

    # Antes de cerrar la fase no se muestra nada.
    antes = client.get(f"/proyectos/{proyecto_id}/mi-retroalimentacion", headers=headers[1]).json()
    assert antes == {"fases": [], "fase_en_curso": 1}

    assert client.post(f"/proyectos/{proyecto_id}/cerrar-fase", headers=headers[0]).status_code == 200
    datos = client.get(f"/proyectos/{proyecto_id}/mi-retroalimentacion", headers=headers[1]).json()
    assert datos["fase_en_curso"] == 2
    fase = datos["fases"][0]
    assert fase["fase"] == 1 and fase["evaluaciones"] == 2 and fase["anonima"] is True
    assert fase["comunicacion"] == 4 and fase["calidad"] == 4 and fase["compromiso"] == 4.5
    assert fase["promedio"] == 4.17
    assert fase["confirmaciones"] == 2
    # Ordenados alfabéticamente: no revelan quién escribió qué.
    assert fase["fortalezas"] == ["Buen diseño", "Siempre avisó sus avances"]
    assert fase["mejoras"] == ["Revisar ortografía"]
    # La respuesta no incluye a los evaluadores.
    assert "evaluador_id" not in str(datos)

    # Cada quien recibe el aviso.
    titulos = [n["titulo"] for n in client.get("/notificaciones", headers=headers[1]).json()["notificaciones"]]
    assert "Ya puedes ver tu retroalimentación de la fase 1" in titulos


def test_solo_la_propia_y_equipo_de_dos_no_anonimo(client: TestClient):
    proyecto_id, usuarios, headers = equipo(client, "Lider", "Ana")
    lider, ana = usuarios
    for i, usuario in enumerate(usuarios):
        act = actividad(client, proyecto_id, headers[0], usuario["id"], 4, f"Tarea {i}")
        votar_todos(client, act, headers, 4)
        completar(client, act, headers[i], headers[1 - i])
    calificar(client, proyecto_id, headers[0], ana["id"], (4, 4, 4), mejora="Llegar a tiempo")
    calificar(client, proyecto_id, headers[1], lider["id"], (5, 5, 5))
    client.post(f"/proyectos/{proyecto_id}/cerrar-fase", headers=headers[0])

    ana_fase = client.get(f"/proyectos/{proyecto_id}/mi-retroalimentacion", headers=headers[1]).json()["fases"][0]
    assert ana_fase["anonima"] is False and ana_fase["mejoras"] == ["Llegar a tiempo"]
    # El líder ve la suya, no la de Ana.
    lider_fase = client.get(f"/proyectos/{proyecto_id}/mi-retroalimentacion", headers=headers[0]).json()["fases"][0]
    assert lider_fase["mejoras"] == [] and lider_fase["comunicacion"] == 5
    # Alguien de fuera no puede consultarla.
    from test_iteracion1 import login, register

    register(client, "Extra", "extra@example.com")
    extra = login(client, "extra@example.com")
    assert client.get(f"/proyectos/{proyecto_id}/mi-retroalimentacion", headers=extra).status_code == 403


def test_comentarios_largos_se_rechazan(client: TestClient):
    proyecto_id, (lider, ana, beto), headers = preparar(client)
    respuesta = client.post(
        f"/proyectos/{proyecto_id}/evaluaciones",
        json={"evaluado_id": ana["id"], "comunicacion": 3, "calidad": 3, "compromiso": 3, "mejora": "x" * 501},
        headers=headers[0],
    )
    assert respuesta.status_code == 422
