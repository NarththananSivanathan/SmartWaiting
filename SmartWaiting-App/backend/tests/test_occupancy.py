from unittest.mock import patch, AsyncMock

IA_RESPONSE = {
    "duree_par_patient": 22.0,
    "temps_attente_min": 88.0,
    "heure_passage": "14h30",
    "message": "Vous êtes en position 4.",
    "type_rdv": "Consultation générale",
    "jour_semaine": "Lundi",
    "saison_annee": "Été",
}


# ──────────────────────────────────────────────────────────────
# POST /
# ──────────────────────────────────────────────────────────────

def test_receive_sensor(client):
    """Le capteur IoT envoie une mesure et elle est stockée avec source='sensor'."""
    res = client.post("/api/occupancy/", json={
        "occupied_chairs": 10,
        "patient_position": 11,
        "room_id": "salle_1",
    })
    assert res.status_code == 201
    data = res.json()
    assert data["occupied_count"] == 10
    assert data["patient_position"] == 11
    assert data["source"] == "sensor"
    assert "timestamp" in data


def test_receive_sensor_sans_position(client):
    """patient_position est optionnel."""
    res = client.post("/api/occupancy/", json={"occupied_chairs": 5})
    assert res.status_code == 201
    assert res.json()["patient_position"] is None


# ──────────────────────────────────────────────────────────────
# GET /latest
# ──────────────────────────────────────────────────────────────

def test_latest_aucune_donnee(client):
    res = client.get("/api/occupancy/latest")
    assert res.status_code == 404


def test_latest_retourne_la_plus_recente(client):
    """Parmi plusieurs mesures, /latest retourne la plus récente."""
    client.post("/api/occupancy/", json={"occupied_chairs": 3})
    client.post("/api/occupancy/", json={"occupied_chairs": 9})
    res = client.get("/api/occupancy/latest")
    assert res.status_code == 200
    assert res.json()["occupied_count"] == 9


# ──────────────────────────────────────────────────────────────
# GET /waiting-time
# ──────────────────────────────────────────────────────────────

def test_waiting_time_aucune_donnee(client):
    res = client.get("/api/occupancy/waiting-time")
    assert res.status_code == 404


def test_waiting_time(client):
    """waiting-time lit la dernière mesure et appelle l'IA."""
    client.post("/api/occupancy/", json={"occupied_chairs": 4, "patient_position": 5})
    with patch("app.routers.occupancy._call_ia", new=AsyncMock(return_value=IA_RESPONSE)):
        res = client.get("/api/occupancy/waiting-time")
    assert res.status_code == 200
    data = res.json()
    assert data["nb_personnes"] == 4
    assert data["patient_position"] == 5
    assert data["temps_attente_min"] == 88.0
    assert data["source_occupancy"] == "sensor"
    assert data["heure_passage"] == "14h30"


def test_waiting_time_utilise_la_plus_recente(client):
    """waiting-time ne prend que la dernière mesure, pas la première."""
    client.post("/api/occupancy/", json={"occupied_chairs": 2})
    client.post("/api/occupancy/", json={"occupied_chairs": 12, "patient_position": 13})
    with patch("app.routers.occupancy._call_ia", new=AsyncMock(return_value=IA_RESPONSE)):
        res = client.get("/api/occupancy/waiting-time")
    assert res.status_code == 200
    assert res.json()["nb_personnes"] == 12


def test_waiting_time_position_fallback(client):
    """Si patient_position est None, on utilise occupied_count comme position."""
    client.post("/api/occupancy/", json={"occupied_chairs": 7})
    ia_mock = AsyncMock(return_value=IA_RESPONSE)
    with patch("app.routers.occupancy._call_ia", new=ia_mock):
        client.get("/api/occupancy/waiting-time")
    # _call_ia doit avoir été appelé avec position=7
    ia_mock.assert_called_once_with(7, "Consultation générale")


def test_waiting_time_ia_erreur(client):
    """Si l'IA est indisponible, le backend retourne 502."""
    from fastapi import HTTPException
    client.post("/api/occupancy/", json={"occupied_chairs": 3})
    with patch("app.routers.occupancy._call_ia", new=AsyncMock(
        side_effect=HTTPException(status_code=502, detail="Erreur service IA")
    )):
        res = client.get("/api/occupancy/waiting-time")
    assert res.status_code == 502
