# Tests — SmartWaiting YOLO (Service caméra)

Tests automatisés du script de détection caméra `camera_occupancy_sensor.py`. Couvrent la fonction d'envoi au backend et l'intégration de la boucle de stream.

---

## Stack de test

| Outil | Rôle |
|-------|------|
| `pytest` | Framework de test |
| `unittest.mock` | Simule `urllib.request.urlopen` — pas de vraie requête HTTP |
| `FauxModele` | Remplace YOLO — retourne toujours 2 personnes sans télécharger le modèle |
| `FauxCapture` | Remplace `cv2.VideoCapture` — génère N frames noires en mémoire |

---

## Lancer les tests

### Dans Docker (recommandé)

```bash
# Installer pytest dans le container YOLO (une seule fois)
docker exec SmartWaiting-YOLO pip install pytest

# Lancer les tests
docker exec SmartWaiting-YOLO python -m pytest test_camera_backend.py -v
```

### Un seul test

```bash
docker exec SmartWaiting-YOLO python -m pytest test_camera_backend.py::test_envoyer_au_backend_payload_correct -v
```

---

## Structure des fichiers

```
SmartWaiting-YOLO/
├── camera_occupancy_sensor.py   # Code testé : _envoyer_au_backend() + stream()
├── test_camera_backend.py       # 7 tests — intégration backend
├── image_occupancy_sensor.py
├── yolo_detection.py
├── occupancy_logic.py
├── api.py
└── requirements.txt
```

---

## Principe des tests

Les tests **ne téléchargent pas YOLO** et **n'envoient pas de vraie requête HTTP**. Tout est simulé :

```
FauxCapture.read()          → génère des frames noires (numpy)
FauxModele.__call__()       → retourne toujours 2 personnes détectées
urllib.request.urlopen()    → intercepté par unittest.mock (patch)
```

Cela permet de tester la logique de `_envoyer_au_backend` et de `stream()` sans dépendance externe.

---

## test_camera_backend.py — 7 tests

### _envoyer_au_backend()

Fonction qui envoie le nombre de places occupées au backend SmartWaiting via HTTP POST.

| Test | Ce qui est vérifié |
|------|--------------------|
| `test_envoyer_au_backend_payload_correct` | Le corps JSON contient `occupied_chairs` avec la bonne valeur et `source="camera"` |
| `test_envoyer_au_backend_url_correcte` | La requête est bien envoyée à `{backend_url}/api/occupancy/` |
| `test_envoyer_au_backend_slash_final_normalise` | Un slash en trop dans l'URL est nettoyé (`http://host:8000/` → `http://host:8000/api/occupancy/`) |
| `test_envoyer_au_backend_erreur_ne_plante_pas` | Une erreur réseau (connexion refusée) est capturée silencieusement — la boucle ne s'arrête pas |
| `test_envoyer_au_backend_content_type_json` | Le header `Content-Type: application/json` est bien présent dans la requête |

### CapteurOccupationCamera.stream() avec backend_url

| Test | Ce qui est vérifié |
|------|--------------------|
| `test_stream_appelle_backend_pour_chaque_frame` | Avec `backend_url` défini, `_envoyer_au_backend` est appelé après chaque frame analysée avec la bonne URL et le bon compte |
| `test_stream_sans_backend_url_ne_plante_pas` | Sans `backend_url`, `_envoyer_au_backend` n'est jamais appelé — comportement identique à l'original |

---

## Résultat attendu

```
======================== 7 passed in 0.15s =========================
```

---

## Dépendances de test

pytest n'est pas dans `requirements.txt` (non nécessaire en production). À installer uniquement pour les tests :

```bash
pip install pytest
python -m pytest test_camera_backend.py -v
```