# SmartWaiting — App

Cœur de l'application SmartWaiting. Gère les consultations médicales, l'occupation de la salle d'attente en temps réel, et orchestre les prédictions IA. Composé d'un backend FastAPI, d'un frontend Next.js et d'une base de données MySQL.

---

## Structure

```
SmartWaiting-App/
├── backend/
│   ├── app/
│   │   ├── main.py              # Point d'entrée FastAPI, CORS
│   │   ├── config.py            # Variables d'environnement (DATABASE_URL, IA_API_URL, YOLO_API_URL)
│   │   ├── database.py          # Connexion SQLAlchemy, session get_db()
│   │   ├── models.py            # Tables : Consultation, OccupancyReading
│   │   ├── schemas.py           # Schémas Pydantic (validation entrée/sortie)
│   │   └── routers/
│   │       ├── consultations.py # CRUD consultations
│   │       └── occupancy.py     # Occupation salle + prédiction temps d'attente
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── app/
│   │   │   ├── page.tsx         # Page consultations (médecin)
│   │   │   ├── attente/
│   │   │   │   └── page.tsx     # Page salle d'attente (patient)
│   │   │   ├── layout.tsx       # Layout global
│   │   │   └── globals.css      # Styles globaux
│   │   └── lib/
│   │       └── api.ts           # Toutes les fonctions d'appel API
│   ├── package.json
│   └── Dockerfile
└── mysql/
    └── init.sql                 # Création de la base smartwaiting
```

---

## Base de données

### Table `consultations`

Enregistre chaque consultation médicale. Alimentée par le médecin via la page `/`.

| Colonne | Type | Description |
|---------|------|-------------|
| `id` | INT | Identifiant auto-incrémenté |
| `heure_arrivee` | DATETIME | Heure de début (clic "Commencer") |
| `heure_depart` | DATETIME | Heure de fin (clic "Quitter"), NULL si en cours |
| `date` | DATE | Date de la consultation |
| `duree_consultation` | INT | Durée en minutes (calculée à la fin) |
| `jour_semaine` | VARCHAR | Lundi … Samedi (dérivé automatiquement) |
| `saison_annee` | VARCHAR | Hiver / Printemps / Été / Automne (dérivé) |
| `type_rdv` | VARCHAR | Type de rendez-vous choisi par le médecin |

### Table `occupancy_readings`

Enregistre chaque mesure d'occupation reçue, qu'elle vienne du capteur IoT ou de l'analyse YOLO.

| Colonne | Type | Description |
|---------|------|-------------|
| `id` | INT | Identifiant auto-incrémenté |
| `occupied_count` | INT | Nombre de places occupées détectées |
| `patient_position` | INT | Position du prochain patient dans la file |
| `source` | VARCHAR | `"sensor"` (IoT) ou `"yolo"` (caméra) |
| `timestamp` | DATETIME | Horodatage de la mesure |

---

## API Endpoints

### Consultations — `/api/consultations`

| Méthode | Endpoint | Description |
|---------|----------|-------------|
| `POST` | `/start` | Démarre une consultation, stocke l'heure d'arrivée |
| `PATCH` | `/{id}/end` | Termine la consultation, calcule la durée |
| `PATCH` | `/{id}/type` | Met à jour le type de rendez-vous |
| `GET` | `/` | Liste paginée (`?page=1&size=20`) |
| `GET` | `/{id}` | Détail d'une consultation |

**Exemple — démarrer une consultation :**
```bash
curl -X POST http://localhost:8000/api/consultations/start \
  -H "Content-Type: application/json" \
  -d '{"type_rdv": "Urgence"}'
```

**Exemple — réponse paginée :**
```json
{
  "total": 42,
  "page": 1,
  "size": 20,
  "pages": 3,
  "data": [...]
}
```

### Occupation — `/api/occupancy`

| Méthode | Endpoint | Description |
|---------|----------|-------------|
| `POST` | `/` | Reçoit les données du capteur IoT |
| `POST` | `/analyser` | Reçoit une image → YOLO détecte → IA prédit |
| `GET` | `/waiting-time` | Temps d'attente estimé (lit dernière mesure + appelle IA) |
| `GET` | `/latest` | Dernière mesure d'occupation brute |

**Exemple — temps d'attente :**
```bash
curl http://localhost:8000/api/occupancy/waiting-time
```
```json
{
  "nb_personnes": 8,
  "patient_position": 9,
  "duree_par_patient": 22.5,
  "temps_attente_min": 180.0,
  "heure_passage": "14h30",
  "type_rdv": "Consultation générale",
  "jour_semaine": "Mardi",
  "saison_annee": "Été",
  "source_occupancy": "sensor",
  "timestamp": "2026-06-23T10:00:00"
}
```

### Autres

| Méthode | Endpoint | Description |
|---------|----------|-------------|
| `GET` | `/health` | Health check du backend |
| `GET` | `/docs` | Documentation Swagger interactive |

---

## Flux de données

```
Capteur IoT
    │  POST /api/occupancy/
    ▼
Backend ──── INSERT ────▶ MySQL (occupancy_readings)

Caméra (image JPEG)
    │  POST /api/occupancy/analyser
    ▼
Backend ──── appelle ───▶ SmartWaiting-YOLO (détection personnes)
    │                              │
    │         occupied_count ◀─────┘
    │
    ├── INSERT ────▶ MySQL (occupancy_readings, source="yolo")
    └── appelle ───▶ SmartWaiting-IA (prédiction temps d'attente)
                              │
              WaitingTimeResponse ◀────┘

Frontend (patient) — GET /api/occupancy/waiting-time
    ▼
Backend ──── SELECT ────▶ MySQL (dernière mesure)
    │
    └── appelle ───▶ SmartWaiting-IA (prédiction à la demande)
                              │
              WaitingTimeResponse ◀────┘
```

---

## Frontend

### Page `/` — Interface médecin

- Démarrer / terminer une consultation
- Choisir le type de rendez-vous
- Voir l'historique paginé des consultations

### Page `/attente` — Affichage patient

- Position dans la file d'attente
- Temps d'attente estimé (mis à jour toutes les 30 secondes)
- Heure de passage estimée
- Upload d'une image pour analyse YOLO en direct

---

## Types de rendez-vous

```
Consultation générale · Consultation de suivi · Urgence
Vaccination · Bilan de santé · Autre
```

---

## Variables d'environnement

Définies dans `.env` à la racine du projet :

| Variable | Valeur par défaut | Usage |
|----------|-------------------|-------|
| `MYSQL_USER` | `user` | Connexion MySQL |
| `MYSQL_PASSWORD` | `password` | Connexion MySQL |
| `MYSQL_ROOT_PASSWORD` | `rootpassword` | Init MySQL |
| `SECRET_KEY` | `changeme-in-production` | Sécurité backend |
| `NEXT_PUBLIC_API_URL` | `http://localhost:8000` | URL backend appelée par le navigateur |

---

## Connexion directe à la base de données

```bash
docker exec SmartWaiting-BDD mysql -uuser -ppassword smartwaiting -e "SELECT * FROM consultations ORDER BY heure_arrivee DESC LIMIT 10;"
docker exec SmartWaiting-BDD mysql -uuser -ppassword smartwaiting -e "SELECT * FROM occupancy_readings ORDER BY timestamp DESC LIMIT 10;"
```

Ou via un client SQL (DBeaver, DataGrip…) :

```
Host     : localhost
Port     : 3306
Base     : smartwaiting
User     : user
Password : password
```

---

## Export des consultations pour réentraîner l'IA

Les données réelles accumulées dans MySQL peuvent servir à améliorer le modèle IA (`SmartWaiting-IA/03_train_model.py`) :

```bash
docker exec SmartWaiting-BDD mysql -uuser -ppassword smartwaiting \
  -e "SELECT heure_arrivee, heure_depart, date, duree_consultation, jour_semaine, saison_annee, type_rdv FROM consultations WHERE duree_consultation > 0" \
  > ../SmartWaiting-IA/data/consultations.csv
```