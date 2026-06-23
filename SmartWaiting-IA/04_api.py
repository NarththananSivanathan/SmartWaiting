from flask import Flask, request, jsonify
import joblib
import pandas as pd
import json
from datetime import datetime, timedelta
from utils import JOURS_FR, get_saison

# ─────────────────────────────────────────
# CHARGEMENT DU MODÈLE ET ENCODEURS
# ─────────────────────────────────────────
model     = joblib.load("models/model_smartwaiting.pkl")
le_jour   = joblib.load("models/le_jour.pkl")
le_saison = joblib.load("models/le_saison.pkl")
le_type   = joblib.load("models/le_type.pkl")

with open("models/features.json", encoding="utf-8") as f:
    meta = json.load(f)

FEATURES        = meta["features"]
TYPES_VALIDES   = meta["types_valides"]
JOURS_VALIDES   = meta["jours_valides"]
SAISONS_VALIDES = meta["saisons_valides"]

app = Flask(__name__)

# ─────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────
def predire(heure_decimal: float, minute: int, mois: int,
            jour_str: str, saison_str: str, type_str: str) -> float:
    """Prédit la durée d'une consultation à partir des features."""
    jour_enc   = le_jour.transform([jour_str])[0]
    saison_enc = le_saison.transform([saison_str])[0]
    type_enc   = le_type.transform([type_str])[0]

    X = pd.DataFrame(
        [[heure_decimal, minute, mois, jour_enc, saison_enc, type_enc]],
        columns=FEATURES
    )
    return float(model.predict(X)[0])

# ─────────────────────────────────────────
# ROUTES
# ─────────────────────────────────────────
@app.route("/", methods=["GET"])
def home():
    return jsonify({
        "status"          : "ok",
        "message"         : "SmartWaiting IA API v3",
        "routes"          : [
            "GET  /",
            "POST /predict       (paramètres manuels)",
            "POST /predict/auto  (heure/jour/saison auto)",
            "GET  /types         (liste des types de RDV)",
        ],
        "types_valides"   : TYPES_VALIDES,
        "jours_valides"   : JOURS_VALIDES,
        "saisons_valides" : SAISONS_VALIDES,
    })


@app.route("/types", methods=["GET"])
def get_types():
    """Liste les types de consultations acceptés par le modèle."""
    return jsonify({
        "types_valides"   : TYPES_VALIDES,
        "jours_valides"   : JOURS_VALIDES,
        "saisons_valides" : SAISONS_VALIDES,
    })


@app.route("/predict", methods=["POST"])
def predict():
    """
    Prédit le temps d'attente avec des paramètres fournis manuellement.

    Body JSON attendu :
    {
        "position"        : 3,                       # position dans la file (1–50)
        "heure_arrivee"   : "10:30",                 # heure d'arrivée HH:MM
        "jour_semaine"    : "Lundi",
        "saison_annee"    : "Hiver",
        "type_rdv"        : "Consultation générale"
    }
    """
    try:
        data = request.get_json()

        position    = int(data.get("position", 1))
        heure_str   = data.get("heure_arrivee", "10:00")
        jour        = data.get("jour_semaine", "Lundi")
        saison      = data.get("saison_annee", "Printemps")
        type_rdv    = data.get("type_rdv", "Consultation générale")

        # Validation
        if position < 1 or position > 50:
            return jsonify({"error": "La position doit être entre 1 et 50"}), 400
        if jour not in JOURS_VALIDES:
            return jsonify({"error": f"Jour invalide. Valeurs acceptées : {JOURS_VALIDES}"}), 400
        if saison not in SAISONS_VALIDES:
            return jsonify({"error": f"Saison invalide. Valeurs acceptées : {SAISONS_VALIDES}"}), 400
        if type_rdv not in TYPES_VALIDES:
            return jsonify({"error": f"Type de RDV invalide. Valeurs acceptées : {TYPES_VALIDES}"}), 400

        # Parsing de l'heure
        h, m = map(int, heure_str.split(":"))
        heure_decimal = h + m / 60

        # Mois estimé selon la saison
        mois_saison = {"Hiver": 1, "Printemps": 4, "Été": 7, "Automne": 10}
        mois = mois_saison.get(saison, 6)

        duree_predite     = predire(heure_decimal, m, mois, jour, saison, type_rdv)
        duree_predite     = round(max(5.0, duree_predite), 1)
        temps_attente_min = round(position * duree_predite, 1)

        # Calcul de l'heure de passage
        maintenant    = datetime.now().replace(hour=h, minute=m, second=0, microsecond=0)
        heure_passage = maintenant + timedelta(minutes=temps_attente_min)

        return jsonify({
            "position"          : position,
            "heure_arrivee"     : heure_str,
            "jour_semaine"      : jour,
            "saison_annee"      : saison,
            "type_rdv"          : type_rdv,
            "duree_par_patient" : duree_predite,
            "temps_attente_min" : temps_attente_min,
            "heure_passage"     : heure_passage.strftime("%Hh%M"),
            "message"           : (
                f"Vous êtes en position {position}. "
                f"Durée estimée par patient : {duree_predite} min. "
                f"Attente totale : {temps_attente_min} min. "
                f"Passage estimé à {heure_passage.strftime('%Hh%M')}."
            )
        })

    except ValueError as ve:
        return jsonify({"error": f"Format invalide : {str(ve)}"}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/predict/auto", methods=["POST"])
def predict_auto():
    """
    Prédit le temps d'attente en détectant automatiquement
    l'heure courante, le jour et la saison.

    Body JSON attendu :
    {
        "position" : 3,
        "type_rdv" : "Urgence"
    }
    """
    try:
        data     = request.get_json()
        position = int(data.get("position", 1))
        type_rdv = data.get("type_rdv", "Consultation générale")

        if position < 1 or position > 50:
            return jsonify({"error": "La position doit être entre 1 et 50"}), 400
        if type_rdv not in TYPES_VALIDES:
            return jsonify({"error": f"Type de RDV invalide. Valeurs acceptées : {TYPES_VALIDES}"}), 400

        now           = datetime.now()
        heure_decimal = max(7.5, min(18.99, now.hour + now.minute / 60))
        minute        = now.minute
        mois          = now.month
        jour_str      = JOURS_FR.get(now.weekday(), "Lundi")
        saison        = get_saison(now.month)

        duree_predite     = predire(heure_decimal, minute, mois, jour_str, saison, type_rdv)
        duree_predite     = round(max(5.0, duree_predite), 1)
        temps_attente_min = round(position * duree_predite, 1)
        heure_passage     = now + timedelta(minutes=temps_attente_min)

        return jsonify({
            "position"          : position,
            "heure_arrivee"     : now.strftime("%Hh%M"),
            "jour_semaine"      : jour_str,
            "saison_annee"      : saison,
            "type_rdv"          : type_rdv,
            "duree_par_patient" : duree_predite,
            "temps_attente_min" : temps_attente_min,
            "heure_passage"     : heure_passage.strftime("%Hh%M"),
            "message"           : (
                f"Vous êtes en position {position}. "
                f"Durée estimée par patient : {duree_predite} min. "
                f"Attente totale : {temps_attente_min} min. "
                f"Passage estimé à {heure_passage.strftime('%Hh%M')}."
            )
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ─────────────────────────────────────────
# POINT D'ENTRÉE
# ─────────────────────────────────────────
if __name__ == "__main__":
    print("🚀 SmartWaiting IA API v3 démarrée !")
    print("📡 http://localhost:5000")
    print(f"🌍 Saison actuelle : {get_saison(datetime.now().month)}")
    print(f"📋 Types de RDV ({len(TYPES_VALIDES)}) : {TYPES_VALIDES}")
    app.run(debug=True, host="0.0.0.0", port=5000)