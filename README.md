# SmartWaiting

Système intelligent de gestion de file d'attente médicale. Combine un capteur IoT, de la détection visuelle par IA (YOLO), un modèle Machine Learning de prédiction, et une application web temps réel pour afficher au patient son temps d'attente estimé.

---

## Vue d'ensemble

```
┌─────────────────────────────────────────────────────────────────┐
│                        SmartWaiting                             │
│                                                                 │
│   IoT Capteur          YOLO                    IA               │
│   (simulation          (détection              (prédiction      │
│    25 chaises)          caméra)                 ML)             │
│       │                   │                     ▲               │
│       │ POST              │ POST                │               │
│       ▼                   ▼                     │               │
│            ┌──────────────────────┐             │               │
│            │       Backend        │─────────────┘               │
│            │       FastAPI        │  appelle à la demande       │
│            │       MySQL          │                             │
│            └──────────────────────┘                             │
│                       │                                         │
│                       │ JSON                                    │
│                       ▼                                         │
│            ┌──────────────────────┐                             │
│            │      Frontend        │                             │
│            │      Next.js         │                             │
│            └──────────────────────┘                             │
└─────────────────────────────────────────────────────────────────┘
```

---

## Les 4 modules

| Module | Rôle | Port | Tech |
|--------|------|------|------|
| [SmartWaiting-App](./SmartWaiting-App/README.md) | Backend API + Frontend + MySQL | 8000 / 3000 / 3306 | FastAPI · Next.js · MySQL |
| [SmartWaiting-IA](./SmartWaiting-IA/README.md) | Prédiction du temps d'attente (ML) | 5000 | Flask · scikit-learn · Random Forest |
| [SmartWaiting-YOLO](./SmartWaiting-YOLO/README.md) | Détection des personnes sur image caméra | 8001 | FastAPI · YOLOv8 · OpenCV |
| [SmartWaiting-IoT-Capteur](./SmartWaiting-IoT-Capteur/README.md) | Simulateur de capteur d'occupation | — | Python stdlib |

---

## Prérequis

Un seul outil à installer : **Docker Desktop**. Il inclut Docker et Docker Compose.

| Outil | Version minimum | Téléchargement |
|-------|----------------|----------------|
| Docker Desktop | 4.x | [docs.docker.com/get-docker](https://docs.docker.com/get-docker/) |

Vérifier que Docker est bien installé :

```bash
docker --version        # Docker version 24.x ou supérieur
docker compose version  # Docker Compose version 2.x ou supérieur
```

> Aucune installation de Python, Node.js ou MySQL n'est nécessaire — tout tourne dans des conteneurs.

---

## Installation et démarrage

```bash
# 1. Cloner le projet
git clone https://github.com/NarththananSivanathan/SmartWaiting
cd SmartWaiting

# 2. Créer le fichier d'environnement
cp .env.example .env

# 3. Construire et lancer tous les services
docker compose up --build
```

Le premier lancement télécharge les images Docker et compile le frontend (~2-3 minutes).

L'application est disponible sur **http://localhost:3000**

---

## Accès aux services

| Service | URL | Description |
|---------|-----|-------------|
| **Frontend** | http://localhost:3000 | Interface médecin + salle d'attente |
| **Backend API** | http://localhost:8000 | API REST FastAPI |
| **Swagger** | http://localhost:8000/docs | Documentation interactive de l'API |
| **IA API** | http://localhost:5000 | Prédiction temps d'attente |
| **YOLO API** | http://localhost:8001 | Détection visuelle |
| **MySQL** | localhost:3306 | Base de données (user / password) |

---

## Flux de données complet

### 1 — Capteur IoT → Backend (toutes les 30s)

```
sensor_simulator.py
    └── POST /api/occupancy/
            └── MySQL : INSERT occupancy_readings (source="sensor")
```

### 2 — Analyse caméra → Backend → YOLO → IA

```
Frontend (upload image)
    └── POST /api/occupancy/analyser
            ├── POST http://yolo:8001/analyser  →  occupied_count
            ├── MySQL : INSERT occupancy_readings (source="yolo")
            └── POST http://ia:5000/predict/auto  →  temps d'attente
```

### 3 — Patient consulte son temps d'attente

```
Frontend GET /attente (toutes les 30s)
    └── GET /api/occupancy/waiting-time
            ├── MySQL : SELECT dernière mesure
            └── POST http://ia:5000/predict/auto  →  temps d'attente
```

### 4 — Médecin enregistre une consultation

```
Frontend (clic "Commencer")
    └── POST /api/consultations/start
            └── MySQL : INSERT consultations

Frontend (clic "Quitter")
    └── PATCH /api/consultations/{id}/end
            └── MySQL : UPDATE consultations (heure_depart, duree)
```

---

## Variables d'environnement

Toutes définies dans `.env` à la racine :

```env
# MySQL
MYSQL_ROOT_PASSWORD=rootpassword
MYSQL_USER=user
MYSQL_PASSWORD=password

# Backend
SECRET_KEY=changeme-in-production

# Frontend (URL appelée par le navigateur)
NEXT_PUBLIC_API_URL=http://localhost:8000

# IoT
IOT_INTERVAL=30
```

---

## Commandes utiles

```bash
# Lancer tous les services
docker compose up --build

# Lancer en arrière-plan
docker compose up -d --build

# Voir les logs d'un service
docker compose logs -f backend
docker compose logs -f ia
docker compose logs -f iot

# Arrêter tous les services
docker compose down

# Arrêter et supprimer les volumes (réinitialise la BDD)
docker compose down -v

# Reconstruire un seul service
docker compose build ia
docker compose up -d ia
```

---

## Inspecter la base de données

```bash
# Dernières mesures IoT
docker exec SmartWaiting-BDD mysql -uuser -ppassword smartwaiting \
  -e "SELECT * FROM occupancy_readings ORDER BY timestamp DESC LIMIT 10;"

# Historique des consultations
docker exec SmartWaiting-BDD mysql -uuser -ppassword smartwaiting \
  -e "SELECT * FROM consultations ORDER BY heure_arrivee DESC LIMIT 10;"
```

---

## Modèle IA — performances

Le modèle Random Forest est entraîné sur 1500 consultations médicales simulées.

| Métrique | Valeur |
|----------|--------|
| R² | 0.755 |
| MAE | 3.50 min |
| RMSE | 4.60 min |

Pour améliorer le modèle avec les vraies données accumulées dans MySQL, voir [SmartWaiting-IA/README.md](./SmartWaiting-IA/README.md#réentraîner-avec-les-vraies-données).

---

## Structure du projet

```
SmartWaiting/
├── docker-compose.yml            # Orchestration de tous les services
├── .env.example                  # Template des variables d'environnement
├── .env                          # Variables d'environnement (non versionné)
├── README.md                     # Ce fichier
│
├── SmartWaiting-App/             # Backend + Frontend + MySQL
│   ├── backend/                  # FastAPI (port 8000)
│   ├── frontend/                 # Next.js (port 3000)
│   └── mysql/                    # Script d'initialisation BDD
│
├── SmartWaiting-IA/              # Service de prédiction ML (port 5000)
│   ├── 01_generate_dataset.py    # Génération du dataset d'entraînement
│   ├── 02_visualize.py           # Visualisation du dataset
│   ├── 03_train_model.py         # Entraînement du Random Forest
│   ├── 04_api.py                 # API Flask (production)
│   ├── 05_dashboard.py           # Dashboard interactif (dev local)
│   ├── utils.py                  # Helpers partagés
│   └── models/                   # Modèles .pkl entraînés
│
├── SmartWaiting-YOLO/            # Service de détection visuelle (port 8001)
│   ├── api.py                    # API FastAPI
│   ├── image_occupancy_sensor.py # Classe principale + CLI
│   ├── yolo_detection.py         # Interface ultralytics YOLO
│   └── occupancy_logic.py        # Logique géométrique
│
└── SmartWaiting-IoT-Capteur/     # Simulateur de capteur
    ├── sensor_simulator.py       # Script de simulation
    └── data/                     # Données locales (persistées par Docker)
```
