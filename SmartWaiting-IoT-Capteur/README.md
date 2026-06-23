# SmartWaiting — IoT Capteur

Simulateur de capteur d'occupation. Génère aléatoirement l'état des 25 chaises de la salle d'attente, calcule les métriques d'occupation, et envoie les données au backend SmartWaiting-App toutes les N secondes.

---

## Structure

```
SmartWaiting-IoT-Capteur/
├── sensor_simulator.py   # Script principal — simulation + envoi au backend
├── data/
│   ├── current_state.json      # Dernier état capturé (écrasé à chaque run)
│   └── occupancy_history.csv   # Historique cumulatif de toutes les mesures
├── Dockerfile
└── .dockerignore
```

---

## Ce que fait le capteur

À chaque exécution, `sensor_simulator.py` :

1. **Simule** l'état des 25 chaises (chaque chaise est occupée ou libre avec une probabilité de 50%)
2. **Calcule** les métriques : nombre de chaises occupées / libres, taux d'occupation, position du prochain patient
3. **Enregistre** en local dans `data/current_state.json` et `data/occupancy_history.csv`
4. **Envoie** les données au backend via `POST /api/occupancy/`

---

## Données produites

### `data/current_state.json`

Écrasé à chaque mesure. Contient l'état instantané.

```json
{
  "room_id": "salle_attente_1",
  "timestamp": "2026-06-23 10:30:00",
  "total_chairs": 25,
  "occupied_chairs": 14,
  "free_chairs": 11,
  "occupancy_rate": 56.0,
  "patient_position": 15
}
```

### `data/occupancy_history.csv`

Fichier cumulatif, une ligne ajoutée à chaque mesure.

```
timestamp,occupied_chairs,free_chairs,occupancy_rate,patient_position
2026-06-23 10:30:00,14,11,56.0,15
2026-06-23 11:00:00,9,16,36.0,10
...
```

### Payload envoyé au backend

```json
{
  "room_id": "salle_attente_1",
  "timestamp": "2026-06-23 10:30:00",
  "total_chairs": 25,
  "occupied_chairs": 14,
  "free_chairs": 11,
  "occupancy_rate": 56.0,
  "patient_position": 15
}
```

Le backend stocke `occupied_chairs` comme `occupied_count` et `patient_position` dans la table `occupancy_readings` (source = `"sensor"`).

---

## Flux dans le projet complet

```
sensor_simulator.py
    │  toutes les 30s
    │  POST http://backend:8000/api/occupancy/
    ▼
Backend SmartWaiting-App
    │  INSERT INTO occupancy_readings
    ▼
MySQL (source="sensor")
    │
    └── Frontend /attente  →  GET /api/occupancy/waiting-time
                               → Backend lit dernière mesure
                               → Backend appelle SmartWaiting-IA
                               → Affiche le temps d'attente estimé
```

---

## Variables d'environnement

| Variable | Défaut | Description |
|----------|--------|-------------|
| `BACKEND_URL` | `http://backend:8000/api/occupancy/` | URL du backend à appeler |
| `INTERVAL` | `30` | Secondes entre chaque envoi |

Configurable dans le `.env` à la racine du projet :

```env
IOT_INTERVAL=30
```

---

## Comportement si le backend est inaccessible

Le capteur ne plante pas. En cas d'erreur réseau, il affiche un message et continue :

```
Back-end non joignable : <raison>
```

Les données sont toujours enregistrées localement dans `data/` même si l'envoi échoue.

---

## Lancer en local (sans Docker)

```bash
# Une seule mesure
python sensor_simulator.py

# En boucle toutes les 30 secondes
while true; do python sensor_simulator.py; sleep 30; done
```

---

## Limites et évolutions possibles

| Limite actuelle | Évolution possible |
|----------------|-------------------|
| Occupation simulée aléatoirement (50/50) | Connecter un vrai capteur (PIR, badge RFID, OpenCV sur Raspberry Pi) |
| 25 chaises fixes | Rendre `NB_CHAIRS` configurable via variable d'environnement |
| Données locales non persistées entre redémarrages Docker | Le volume `iot_data` dans `docker-compose.yml` persiste `data/` |
