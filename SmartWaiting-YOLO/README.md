# SmartWaiting — YOLO

Service de détection visuelle. Reçoit une image de la salle d'attente, détecte les personnes avec YOLOv8, et retourne le nombre de places occupées. Exposé via une API FastAPI que le backend SmartWaiting-App appelle.

---

## Structure

```
SmartWaiting-YOLO/
├── api.py                       # API FastAPI — point d'entrée (port 8001)
├── image_occupancy_sensor.py    # Classe principale + usage en ligne de commande
├── yolo_detection.py            # Interface avec la librairie ultralytics YOLO
├── occupancy_logic.py           # Géométrie pure : calcul des places occupées
├── requirements.txt
└── Dockerfile
```

---

## Architecture des modules

```
api.py
  └── CapteurOccupationImage (image_occupancy_sensor.py)
        ├── detecter_personnes()  (yolo_detection.py)   ← parle à YOLO
        └── compter_places_occupees()  (occupancy_logic.py)  ← compte
```

Chaque module a une responsabilité unique. Si le modèle YOLO change de version, seul `yolo_detection.py` est à modifier.

---

## Règle métier : personne détectée = place occupée

L'approche initiale tentait de détecter les chaises puis de vérifier si une personne était assise dessus. En pratique, une chaise occupée est masquée par la personne — YOLO la détecte mal. La règle simplifiée est donc :

> **Nombre de places occupées = nombre de personnes détectées**

Limitation connue : une personne debout (à l'accueil par exemple) est comptée à tort. Ce compromis est volontaire pour la robustesse.

---

## API FastAPI (production) — port 8001

### Endpoints

| Méthode | Endpoint | Description |
|---------|----------|-------------|
| `POST` | `/analyser` | Reçoit une image, retourne le nombre de places occupées |
| `GET` | `/sante` | Health check |

### `POST /analyser`

Reçoit une image en `multipart/form-data`, champ `image`.

```bash
curl -X POST -F "image=@salle_attente.jpg" http://localhost:8001/analyser
```

```json
{
  "occupied_count": 7,
  "timestamp": "2026-06-23T10:30:00+00:00"
}
```

Le modèle YOLO est chargé **une seule fois** au premier appel (via `@lru_cache`) — pas à chaque image reçue, ce qui serait trop lent.

---

## Usage en ligne de commande

`image_occupancy_sensor.py` peut aussi être utilisé directement sans passer par l'API.

### Une seule image

```bash
python image_occupancy_sensor.py \
  --image salle1.jpg \
  --save-annotated salle1_annotee.jpg \
  --csv occupation.csv \
  --conf 0.4
```

### Un dossier d'images (série chronologique)

Utile pour analyser une séquence d'images générées par IA représentant différents moments de la journée. Les images sont traitées dans l'ordre alphabétique.

```bash
python image_occupancy_sensor.py \
  --folder images/ \
  --csv occupation.csv \
  --start-time 2026-06-23T08:00:00 \
  --interval-seconds 600 \
  --annotated-dir images_annotees/
```

### Options disponibles

| Option | Défaut | Description |
|--------|--------|-------------|
| `--image` | — | Chemin d'une image unique |
| `--folder` | — | Dossier contenant plusieurs images |
| `--model` | `yolov8n.pt` | Modèle YOLO à utiliser |
| `--conf` | `0.4` | Seuil de confiance (0–1) |
| `--save-annotated` | — | Chemin de l'image annotée de sortie |
| `--annotated-dir` | — | Dossier de sortie des images annotées |
| `--csv` | `occupation_images.csv` | Fichier CSV de sortie |
| `--start-time` | maintenant | Horodatage ISO de départ (mode dossier) |
| `--interval-seconds` | `60` | Écart simulé entre deux images (mode dossier) |

**Sortie CSV :**
```
timestamp,occupied_count
2026-06-23T08:00:00+00:00,3
2026-06-23T08:10:00+00:00,7
...
```

---

## Flux dans le projet complet

```
Utilisateur (frontend)
    │  upload image
    ▼
Backend SmartWaiting-App
    │  POST http://yolo:8001/analyser
    ▼
api.py  ──▶  CapteurOccupationImage.analyser(image)
                    │
                    ├── detecter_personnes()  →  YOLOv8 (yolov8n.pt)
                    │         retourne liste de boîtes [x1,y1,x2,y2]
                    │
                    └── compter_places_occupees()
                              retourne len(boites_personnes)
    │
    │  {"occupied_count": 7, "timestamp": "..."}
    ▼
Backend  ──▶  stocke dans MySQL  ──▶  appelle SmartWaiting-IA  ──▶  Frontend
```

---

## Détails des modules

### `occupancy_logic.py`

Géométrie pure, aucune dépendance externe. Contient :

- `calculer_iou(boite_a, boite_b)` — calcule le recouvrement (Intersection over Union) entre deux rectangles
- `point_dans_boite(point, boite)` — teste si un point est dans un rectangle
- `chaise_est_occupee(boite_chaise, boites_personnes)` — ancienne approche par correspondance (conservée)
- `compter_places_occupees(boites_personnes)` — **fonction active** : retourne simplement `len(boites_personnes)`

### `yolo_detection.py`

Seul fichier qui interagit avec `ultralytics`. Filtre les détections pour ne garder que la classe `"person"` (classe COCO) avec un seuil de confiance ≥ 0.4.

---

## Modèle YOLO utilisé

**YOLOv8n** (`yolov8n.pt`) — le modèle "nano", le plus léger de la famille YOLOv8. Il se télécharge automatiquement au premier démarrage du conteneur (~6 Mo).

Le modèle n'est **pas réentraîné** — on l'utilise tel quel (inférence uniquement) sur sa classe `person` du dataset COCO.

---

## Installation locale (sans Docker)

```bash
pip install -r requirements.txt
# requirements : fastapi, uvicorn, ultralytics, opencv-python-headless, numpy, python-multipart

uvicorn api:app --host 0.0.0.0 --port 8001
```