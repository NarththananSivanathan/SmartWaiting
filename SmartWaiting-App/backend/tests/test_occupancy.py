from unittest.mock import patch, AsyncMock, MagicMock
import io

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


# ──────────────────────────────────────────────────────────────
# POST / — source dynamique
# ──────────────────────────────────────────────────────────────

def test_receive_sensor_source_defaut(client):
    """Sans champ source, la valeur par défaut est 'sensor'."""
    res = client.post("/api/occupancy/", json={"occupied_chairs": 4})
    assert res.status_code == 201
    assert res.json()["source"] == "sensor"


def test_receive_sensor_source_camera(client):
    """La source 'camera' (script camera_occupancy_sensor.py) est bien stockée."""
    res = client.post("/api/occupancy/", json={"occupied_chairs": 3, "source": "camera"})
    assert res.status_code == 201
    assert res.json()["source"] == "camera"


def test_receive_sensor_source_yolo(client):
    """La source 'yolo' est acceptée et stockée."""
    res = client.post("/api/occupancy/", json={"occupied_chairs": 7, "source": "yolo"})
    assert res.status_code == 201
    assert res.json()["source"] == "yolo"


def test_waiting_time_source_camera(client):
    """source_occupancy reflète bien la source 'camera' dans la réponse waiting-time."""
    client.post("/api/occupancy/", json={"occupied_chairs": 2, "source": "camera"})
    with patch("app.routers.occupancy._call_ia", new=AsyncMock(return_value=IA_RESPONSE)):
        res = client.get("/api/occupancy/waiting-time")
    assert res.status_code == 200
    assert res.json()["source_occupancy"] == "camera"


# ──────────────────────────────────────────────────────────────
# POST /analyser-video
# ──────────────────────────────────────────────────────────────

YOLO_VIDEO_RESPONSE = {
    "resultats": [
        {"frame": 0,  "temps_secondes": 0.0, "occupied_count": 3},
        {"frame": 30, "temps_secondes": 1.0, "occupied_count": 5},
    ],
    "moyenne_occupied": 4.0,
    "nb_frames_analysees": 2,
    "timestamp": "2026-06-24T10:00:00+00:00",
}


def _mock_yolo_client(response_data):
    """Construit un mock httpx.AsyncClient qui retourne response_data."""
    mock_response = MagicMock()
    mock_response.json.return_value = response_data
    mock_response.raise_for_status = MagicMock()

    mock_client = AsyncMock()
    mock_client.post = AsyncMock(return_value=mock_response)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    return mock_client


def test_analyser_video_retourne_resultats(client):
    """analyser-video appelle le service YOLO et retourne les résultats par frame."""
    fake_video = io.BytesIO(b"fake-video-content")
    with patch("httpx.AsyncClient", return_value=_mock_yolo_client(YOLO_VIDEO_RESPONSE)):
        res = client.post(
            "/api/occupancy/analyser-video",
            files={"video": ("test.mp4", fake_video, "video/mp4")},
        )
    assert res.status_code == 201
    data = res.json()
    assert data["moyenne_occupied"] == 4.0
    assert data["nb_frames_analysees"] == 2
    assert len(data["resultats"]) == 2
    assert data["source_occupancy"] == "yolo-video"


def test_analyser_video_stocke_en_base(client):
    """La moyenne est bien stockée en base (vérifiable via /latest)."""
    fake_video = io.BytesIO(b"fake-video-content")
    with patch("httpx.AsyncClient", return_value=_mock_yolo_client(YOLO_VIDEO_RESPONSE)):
        client.post(
            "/api/occupancy/analyser-video",
            files={"video": ("test.mp4", fake_video, "video/mp4")},
        )
    res = client.get("/api/occupancy/latest")
    assert res.status_code == 200
    assert res.json()["occupied_count"] == 4  # round(4.0)
    assert res.json()["source"] == "yolo"


def test_analyser_video_yolo_indisponible(client):
    """Si le service YOLO est indisponible, le backend retourne 502."""
    import httpx
    fake_video = io.BytesIO(b"fake-video-content")
    mock_client = AsyncMock()
    mock_client.post = AsyncMock(side_effect=httpx.HTTPError("connexion refusée"))
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    with patch("httpx.AsyncClient", return_value=mock_client):
        res = client.post(
            "/api/occupancy/analyser-video",
            files={"video": ("test.mp4", fake_video, "video/mp4")},
        )
    assert res.status_code == 502


def test_analyser_video_resultats_par_frame(client):
    """Chaque élément de 'resultats' contient frame, temps_secondes, occupied_count."""
    fake_video = io.BytesIO(b"fake-video-content")
    with patch("httpx.AsyncClient", return_value=_mock_yolo_client(YOLO_VIDEO_RESPONSE)):
        res = client.post(
            "/api/occupancy/analyser-video",
            files={"video": ("test.mp4", fake_video, "video/mp4")},
        )
    premier = res.json()["resultats"][0]
    assert "frame" in premier
    assert "temps_secondes" in premier
    assert "occupied_count" in premier
