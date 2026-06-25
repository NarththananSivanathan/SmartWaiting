"""
Tests pour la fonction _envoyer_au_backend et l'intégration backend
dans camera_occupancy_sensor.py.
"""

import json
from unittest.mock import patch, MagicMock, call

from camera_occupancy_sensor import _envoyer_au_backend, CapteurOccupationCamera


# ──────────────────────────────────────────────────────────────
# _envoyer_au_backend
# ──────────────────────────────────────────────────────────────

def test_envoyer_au_backend_payload_correct():
    """Vérifie que le payload JSON envoyé contient occupied_chairs et source='camera'."""
    requetes_recues = []

    def faux_urlopen(req, timeout=None):
        requetes_recues.append(req)
        return MagicMock().__enter__.return_value

    with patch("urllib.request.urlopen", side_effect=faux_urlopen):
        _envoyer_au_backend("http://localhost:8000", 5)

    assert len(requetes_recues) == 1
    req = requetes_recues[0]
    payload = json.loads(req.data.decode("utf-8"))
    assert payload["occupied_chairs"] == 5
    assert payload["source"] == "camera"


def test_envoyer_au_backend_url_correcte():
    """Vérifie que la requête est envoyée à {backend_url}/api/occupancy/."""
    urls_appelees = []

    def faux_urlopen(req, timeout=None):
        urls_appelees.append(req.full_url)
        return MagicMock().__enter__.return_value

    with patch("urllib.request.urlopen", side_effect=faux_urlopen):
        _envoyer_au_backend("http://backend:8000", 3)

    assert urls_appelees[0] == "http://backend:8000/api/occupancy/"


def test_envoyer_au_backend_slash_final_normalise():
    """Un slash en trop dans l'URL est normalisé (rstrip)."""
    urls_appelees = []

    def faux_urlopen(req, timeout=None):
        urls_appelees.append(req.full_url)
        return MagicMock().__enter__.return_value

    with patch("urllib.request.urlopen", side_effect=faux_urlopen):
        _envoyer_au_backend("http://backend:8000/", 2)

    assert urls_appelees[0] == "http://backend:8000/api/occupancy/"


def test_envoyer_au_backend_erreur_ne_plante_pas():
    """Une erreur réseau ne doit pas faire planter la boucle principale."""
    with patch("urllib.request.urlopen", side_effect=Exception("connexion refusée")):
        # Ne doit lever aucune exception
        _envoyer_au_backend("http://backend:8000", 4)


def test_envoyer_au_backend_content_type_json():
    """Le header Content-Type doit être application/json."""
    requetes_recues = []

    def faux_urlopen(req, timeout=None):
        requetes_recues.append(req)
        return MagicMock().__enter__.return_value

    with patch("urllib.request.urlopen", side_effect=faux_urlopen):
        _envoyer_au_backend("http://localhost:8000", 1)

    assert requetes_recues[0].get_header("Content-type") == "application/json"


# ──────────────────────────────────────────────────────────────
# CapteurOccupationCamera.stream avec backend_url
# ──────────────────────────────────────────────────────────────

class FauxModele:
    """Modèle YOLO simulé — retourne toujours 2 personnes détectées."""
    class FauxBoite:
        cls = [0]
        xyxy = [[10, 10, 50, 90]]

        def tolist(self):
            return [10, 10, 50, 90]

    class FauxResultat:
        names = {0: "person"}
        boxes = None

        def __init__(self):
            boite = FauxModele.FauxBoite()
            boite.xyxy = [type("T", (), {"tolist": lambda self: [10, 10, 50, 90]})()]
            boite.cls = [0]
            self.boxes = [boite, boite]  # 2 personnes

    def __call__(self, image, conf=0.4, verbose=False):
        return [FauxModele.FauxResultat()]


class FauxCapture:
    """Simule cv2.VideoCapture : retourne 3 frames puis s'arrête."""
    import numpy as np

    def __init__(self, nb_frames=3):
        self.nb_frames = nb_frames
        self.compteur = 0

    def read(self):
        if self.compteur < self.nb_frames:
            self.compteur += 1
            import numpy as np
            return True, np.zeros((100, 100, 3), dtype="uint8")
        return False, None


def test_stream_appelle_backend_pour_chaque_frame():
    """Avec backend_url, _envoyer_au_backend est appelé à chaque frame détectée."""
    capteur = CapteurOccupationCamera(modele=FauxModele())
    capture = FauxCapture(nb_frames=3)

    appels = []
    with patch("camera_occupancy_sensor._envoyer_au_backend", side_effect=lambda url, n: appels.append((url, n))):
        capteur.stream(capture, intervalle=0, duree=0.01, backend_url="http://backend:8000")

    assert len(appels) >= 1
    for url, nb in appels:
        assert url == "http://backend:8000"
        assert nb == 2  # FauxModele retourne toujours 2 personnes


def test_stream_sans_backend_url_ne_plante_pas():
    """Sans backend_url, le stream tourne normalement sans appeler _envoyer_au_backend."""
    capteur = CapteurOccupationCamera(modele=FauxModele())
    capture = FauxCapture(nb_frames=2)

    with patch("camera_occupancy_sensor._envoyer_au_backend") as mock_envoyer:
        capteur.stream(capture, intervalle=0, duree=0.01, backend_url=None)

    mock_envoyer.assert_not_called()
