# SmartWaiting — IA

Service de prédiction du temps d'attente. Entraîne un modèle Machine Learning (Random Forest) sur les données de consultations médicales, puis l'expose via une API Flask que le backend peut appeler.

---

## Structure

```
SmartWaiting-IA/
├── 01_generate_dataset.py   # Génère 1500 consultations fictives réalistes
├── 02_visualize.py          # Visualise le dataset (6 graphiques)
├── 03_train_model.py        # Entraîne le Random Forest, sauvegarde les .pkl
├── 04_api.py                # API Flask — point d'entrée en production (port 5000)
├── 05_dashboard.py          # Dashboard interactif local (port 5050)
├── utils.py                 # Helpers partagés : JOURS_FR, get_saison()
├── models/
│   ├── model_smartwaiting.pkl   # Modèle Random Forest entraîné
│   ├── le_jour.pkl              # LabelEncoder jours
│   ├── le_saison.pkl            # LabelEncoder saisons
│   ├── le_type.pkl              # LabelEncoder types de RDV
│   └── features.json            # Liste des features + valeurs valides
├── data/
│   ├── consultations.csv            # Dataset d'entraînement
│   ├── visualisation_dataset.png    # Graphiques générés par 02_visualize.py
│   └── predictions_vs_realite.png   # Courbe prédictions vs réalité
├── requirements.txt
└── Dockerfile
```

---

## Pipeline ML

Les scripts se lancent dans l'ordre. Les modèles sont déjà entraînés et présents dans `models/` — les étapes 1 à 3 ne sont nécessaires que pour réentraîner.

```
01_generate_dataset.py
        │  génère data/consultations.csv (1500 lignes)
        ▼
02_visualize.py
        │  produit data/visualisation_dataset.png
        ▼
03_train_model.py
        │  produit models/*.pkl + models/features.json
        ▼
04_api.py  ◀──── utilisé en production (Docker)
05_dashboard.py  ◀──── utilisé en local (dev)
```

### 01 — Génération du dataset

Crée 1500 consultations fictives avec une logique métier réaliste :

- Durées calibrées par type de RDV (`Urgence` = 35 min, `Vaccination` = 12 min…)
- Effets de l'heure (fin de journée = consultations plus courtes)
- Effets du jour (Lundi = +4 min — accumulation week-end)
- Effets de la saison (Hiver = +4 min — grippe, bronchites)

```bash
python 01_generate_dataset.py
# → data/consultations.csv
```

### 02 — Visualisation

Génère 6 graphiques d'analyse du dataset :

- Durée selon l'heure d'arrivée (nuage de points par type)
- Durée moyenne par tranche horaire
- Durée moyenne par jour de la semaine
- Répartition des types de RDV (camembert)
- Distribution des durées
- Durée moyenne par type × saison

```bash
python 02_visualize.py
# → data/visualisation_dataset.png
```

### 03 — Entraînement

Entraîne un **Random Forest** (200 arbres, profondeur max 12) sur 80% des données, évalue sur 20%.

**Features utilisées :**

| Feature | Description |
|---------|-------------|
| `heure_decimal` | Heure d'arrivée (ex: 10h30 → 10.5) |
| `minute_arrivee` | Minute d'arrivée |
| `mois` | Mois de l'année (1–12) |
| `jour_encode` | Jour encodé (LabelEncoder) |
| `saison_encode` | Saison encodée (LabelEncoder) |
| `type_encode` | Type de RDV encodé (LabelEncoder) |

**Cible :** `duree_consultation` (en minutes)

**Performances actuelles :**

| Métrique | Valeur |
|----------|--------|
| R² | **0.755** |
| MAE | **3.50 min** |
| RMSE | **4.60 min** |

```bash
python 03_train_model.py
# → models/model_smartwaiting.pkl
# → models/le_jour.pkl, le_saison.pkl, le_type.pkl
# → models/features.json
```

---

## API Flask (production) — port 5000

Lancée automatiquement dans Docker via `04_api.py`.

### Endpoints

| Méthode | Endpoint | Description |
|---------|----------|-------------|
| `GET` | `/` | Statut + liste des routes et valeurs valides |
| `GET` | `/types` | Liste des types, jours et saisons acceptés |
| `POST` | `/predict` | Prédiction avec paramètres manuels |
| `POST` | `/predict/auto` | Prédiction avec heure/jour/saison automatiques |

### `POST /predict` — paramètres manuels

```bash
curl -X POST http://localhost:5000/predict \
  -H "Content-Type: application/json" \
  -d '{
    "position": 3,
    "heure_arrivee": "10:30",
    "jour_semaine": "Lundi",
    "saison_annee": "Hiver",
    "type_rdv": "Urgence"
  }'
```

```json
{
  "position": 3,
  "heure_arrivee": "10:30",
  "jour_semaine": "Lundi",
  "saison_annee": "Hiver",
  "type_rdv": "Urgence",
  "duree_par_patient": 38.5,
  "temps_attente_min": 115.5,
  "heure_passage": "12h25",
  "message": "Vous êtes en position 3. Durée estimée par patient : 38.5 min. Attente totale : 115.5 min. Passage estimé à 12h25."
}
```

### `POST /predict/auto` — détecte l'heure/jour/saison automatiquement

Utilisé par le backend SmartWaiting-App pour les calculs en temps réel.

```bash
curl -X POST http://localhost:5000/predict/auto \
  -H "Content-Type: application/json" \
  -d '{"position": 5, "type_rdv": "Consultation générale"}'
```

### Valeurs acceptées

**Types de RDV :**
```
Consultation générale · Consultation de suivi · Urgence
Vaccination · Bilan de santé · Autre
```

**Jours :**
```
Lundi · Mardi · Mercredi · Jeudi · Vendredi · Samedi · Dimanche
```

**Saisons :**
```
Hiver · Printemps · Été · Automne
```

---

## Dashboard local — port 5050

Interface graphique pour tester le modèle sans passer par l'API. Ne tourne **pas** dans Docker — usage développement uniquement.

```bash
pip install -r requirements.txt
python 05_dashboard.py
# → http://localhost:5050
```

Fonctionnalités :
- Slider de position dans la file
- Sélection type / heure / jour / saison
- Bouton "Remplir avec l'heure actuelle"
- Courbe de durée prédite sur toute la journée
- Comparaison des durées par type de RDV

---

## Réentraîner avec les vraies données

Une fois que SmartWaiting-App a accumulé suffisamment de consultations réelles dans MySQL, exporter et réentraîner :

```bash
# 1. Exporter depuis MySQL
docker exec SmartWaiting-BDD mysql -uuser -ppassword smartwaiting \
  -e "SELECT heure_arrivee, heure_depart, date, duree_consultation, jour_semaine, saison_annee, type_rdv FROM consultations WHERE duree_consultation > 0" \
  > data/consultations.csv

# 2. Réentraîner
python 03_train_model.py

# 3. Rebuilder l'image Docker pour embarquer le nouveau modèle
docker compose build ia
docker compose up -d ia
```

---

## Lancer en local (sans Docker)

```bash
pip install -r requirements.txt
python 04_api.py
# → http://localhost:5000
```

---

## Variables d'environnement

Aucune variable requise. L'API charge les modèles depuis `models/` avec des chemins relatifs au répertoire de travail.