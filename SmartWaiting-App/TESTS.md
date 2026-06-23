# Tests — SmartWaiting App (Backend)

Tests automatisés du backend FastAPI. Couvrent les deux routers : consultations et occupation.

---

## Stack de test

| Outil | Rôle |
|-------|------|
| `pytest` | Framework de test |
| `TestClient` (FastAPI) | Simule des requêtes HTTP sans serveur réel |
| `SQLite en mémoire` | Remplace MySQL — base isolée, réinitialisée à chaque test |
| `unittest.mock` | Simule les appels vers l'IA et YOLO (pas de vraie requête HTTP) |

---

## Lancer les tests

### Dans Docker (recommandé)

```bash
docker exec SmartWaiting-Backend python -m pytest tests/ -v
```

### Avec un rapport de couverture

```bash
docker exec SmartWaiting-Backend python -m pytest tests/ -v --tb=short
```

### Un seul fichier

```bash
docker exec SmartWaiting-Backend python -m pytest tests/test_consultations.py -v
docker exec SmartWaiting-Backend python -m pytest tests/test_occupancy.py -v
```

### Un seul test

```bash
docker exec SmartWaiting-Backend python -m pytest tests/test_consultations.py::test_end_consultation -v
```

---

## Structure des fichiers

```
backend/
├── tests/
│   ├── __init__.py
│   ├── conftest.py              # Configuration partagée (DB, client HTTP)
│   ├── test_consultations.py   # 15 tests — router /api/consultations
│   └── test_occupancy.py       #  9 tests — router /api/occupancy
└── requirements-test.txt       # Dépendances de test (pytest)
```

---

## Configuration (conftest.py)

Chaque test reçoit :
- Une base SQLite **en mémoire** → remplace MySQL, aucune donnée réelle touchée
- Un **TestClient** FastAPI → simule les requêtes HTTP
- Une **transaction annulée** après chaque test → la base est propre pour le suivant

```
Test démarre → transaction ouverte → test s'exécute → transaction annulée → base vide
```

---

## tests/test_consultations.py — 15 tests

### POST /api/consultations/start

| Test | Ce qui est vérifié |
|------|--------------------|
| `test_start_consultation_champs_derives` | `jour_semaine` et `saison_annee` sont calculés automatiquement depuis la date courante |
| `test_start_consultation_sans_type` | `type_rdv` est optionnel, peut être `null` |

### PATCH /api/consultations/{id}/end

| Test | Ce qui est vérifié |
|------|--------------------|
| `test_end_consultation` | `heure_depart` et `duree_consultation` sont remplis après la fin |
| `test_end_consultation_introuvable` | Retourne **404** si l'ID n'existe pas |
| `test_end_consultation_deja_terminee` | Retourne **400** si la consultation est déjà terminée |

### PATCH /api/consultations/{id}/type

| Test | Ce qui est vérifié |
|------|--------------------|
| `test_set_type_rdv` | Le type de rendez-vous est bien mis à jour |
| `test_set_type_rdv_introuvable` | Retourne **404** si l'ID n'existe pas |

### GET /api/consultations/

| Test | Ce qui est vérifié |
|------|--------------------|
| `test_list_consultations_vide` | Retourne `total=0` et `data=[]` quand la base est vide |
| `test_list_consultations_pagination` | 5 consultations avec `size=3` → 2 pages, 3 résultats en page 1 |
| `test_list_consultations_page2` | Page 2 retourne les 2 consultations restantes |

### GET /api/consultations/{id}

| Test | Ce qui est vérifié |
|------|--------------------|
| `test_get_consultation` | Retourne la bonne consultation avec ses données |
| `test_get_consultation_introuvable` | Retourne **404** si l'ID n'existe pas |

### GET /api/consultations/stats

| Test | Ce qui est vérifié |
|------|--------------------|
| `test_stats_base_vide` | `total_today=0`, `avg_duree_globale=0.0`, `duree_par_type=[]` |
| `test_stats_compte_aujourd_hui` | Compte correctement le nombre de consultations du jour |
| `test_stats_duree_par_type` | Durées moyennes exactes par type (Urgence: 35.0 min, Vaccination: 12.0 min) |

---

## tests/test_occupancy.py — 9 tests

### POST /api/occupancy/

| Test | Ce qui est vérifié |
|------|--------------------|
| `test_receive_sensor` | La mesure est stockée avec `source="sensor"`, `occupied_count` et `patient_position` corrects |
| `test_receive_sensor_sans_position` | `patient_position` est optionnel, peut être `null` |

### GET /api/occupancy/latest

| Test | Ce qui est vérifié |
|------|--------------------|
| `test_latest_aucune_donnee` | Retourne **404** si aucune mesure n'existe |
| `test_latest_retourne_la_plus_recente` | Parmi plusieurs mesures, retourne toujours la plus récente |

### GET /api/occupancy/waiting-time

| Test | Ce qui est vérifié |
|------|--------------------|
| `test_waiting_time_aucune_donnee` | Retourne **404** si aucune mesure d'occupation n'existe |
| `test_waiting_time` | Lit la dernière mesure, appelle l'IA (mockée), retourne la réponse combinée |
| `test_waiting_time_utilise_la_plus_recente` | Utilise bien la mesure la plus récente, pas la première |
| `test_waiting_time_position_fallback` | Si `patient_position` est `null`, utilise `occupied_count` comme position |
| `test_waiting_time_ia_erreur` | Retourne **502** si le service IA est indisponible |

---

## Résultat attendu

```
======================== 24 passed in 0.15s =========================
```

---

## Dépendances de test

Les dépendances de test sont séparées des dépendances de production dans `requirements-test.txt` :

```
pytest==8.3.3
pytest-asyncio==0.24.0
```

Pour les installer localement (hors Docker) :

```bash
pip install -r requirements.txt -r requirements-test.txt
python -m pytest tests/ -v
```
