import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import joblib
import os
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.preprocessing import LabelEncoder

# ─────────────────────────────────────────
# 1. CHARGEMENT
# ─────────────────────────────────────────
try:
    df = pd.read_csv("data/consultations.csv")
    print("📂 Fichier réel chargé : consultations.csv")
except FileNotFoundError:
    df = pd.read_csv("data/consultations_generated.csv")
    print("📂 Dataset généré chargé : consultations_generated.csv")

print(f"✅ {len(df)} lignes chargées\n")

# ─────────────────────────────────────────
# 2. PRÉ-TRAITEMENT
# ─────────────────────────────────────────
# Parsing des timestamps
df["heure_arrivee"] = pd.to_datetime(df["heure_arrivee"])
df["heure_depart"]  = pd.to_datetime(df["heure_depart"])

# Filtrer les consultations incomplètes (durée = 0)
df = df[df["duree_consultation"] > 0].copy()
print(f"✅ Après filtrage (durée > 0) : {len(df)} lignes\n")

# Feature : heure décimale d'arrivée (ex: 10h30 → 10.5)
df["heure_decimal"] = df["heure_arrivee"].dt.hour + df["heure_arrivee"].dt.minute / 60

# Features supplémentaires extraites des timestamps
df["minute_arrivee"] = df["heure_arrivee"].dt.minute
df["mois"]           = df["heure_arrivee"].dt.month

# ─────────────────────────────────────────
# 3. ENCODAGE DES VARIABLES CATÉGORIELLES
# ─────────────────────────────────────────
le_jour   = LabelEncoder()
le_saison = LabelEncoder()
le_type   = LabelEncoder()

df["jour_encode"]   = le_jour.fit_transform(df["jour_semaine"])
df["saison_encode"] = le_saison.fit_transform(df["saison_annee"])
df["type_encode"]   = le_type.fit_transform(df["type_rdv"])

print("📋 Encodages :")
print(f"  Jours   : {dict(zip(le_jour.classes_, le_jour.transform(le_jour.classes_)))}")
print(f"  Saisons : {dict(zip(le_saison.classes_, le_saison.transform(le_saison.classes_)))}")
print(f"  Types   : {dict(zip(le_type.classes_, le_type.transform(le_type.classes_)))}\n")

print(f"📋 Types de RDV détectés ({len(le_type.classes_)}) :")
for t in le_type.classes_:
    print(f"  - {t}")
print()

# ─────────────────────────────────────────
# 4. FEATURES ET CIBLE
# ─────────────────────────────────────────
FEATURES = ["heure_decimal", "minute_arrivee", "mois", "jour_encode", "saison_encode", "type_encode"]
TARGET   = "duree_consultation"

X = df[FEATURES]
y = df[TARGET]

print(f"📋 Features utilisées : {FEATURES}")
print(f"🎯 Cible : {TARGET}")
print(f"📊 Plage de durées : {y.min()} – {y.max()} min (moy : {y.mean():.1f})\n")

# ─────────────────────────────────────────
# 5. DÉCOUPAGE TRAIN / TEST
# ─────────────────────────────────────────
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42
)
print(f"📊 Entraînement : {len(X_train)} lignes")
print(f"📊 Test         : {len(X_test)} lignes\n")

# ─────────────────────────────────────────
# 6. ENTRAÎNEMENT
# ─────────────────────────────────────────
print("⏳ Entraînement en cours...")
model = RandomForestRegressor(n_estimators=200, max_depth=12, random_state=42, n_jobs=-1)
model.fit(X_train, y_train)
print("✅ Modèle entraîné !\n")

# ─────────────────────────────────────────
# 7. ÉVALUATION
# ─────────────────────────────────────────
y_pred = model.predict(X_test)

mae  = mean_absolute_error(y_test, y_pred)
rmse = np.sqrt(mean_squared_error(y_test, y_pred))
r2   = r2_score(y_test, y_pred)

print("=" * 40)
print("📈 RÉSULTATS DU MODÈLE")
print("=" * 40)
print(f"  MAE  : {mae:.2f} min")
print(f"  RMSE : {rmse:.2f} min")
print(f"  R²   : {r2:.3f}")
print("=" * 40)

if r2 >= 0.85:
    print("🟢 Excellent modèle !")
elif r2 >= 0.70:
    print("🟡 Bon modèle.")
else:
    print("🔴 Modèle à améliorer.")

# ─────────────────────────────────────────
# 8. IMPORTANCE DES FEATURES
# ─────────────────────────────────────────
print("\n📊 Importance des features :")
feat_labels = ["heure", "minute_arrivee", "mois", "jour", "saison", "type_rdv"]
importances = model.feature_importances_
for f, i in sorted(zip(feat_labels, importances), key=lambda x: -x[1]):
    bar = "█" * int(i * 50)
    print(f"  {f:<22} {bar} {i:.3f}")

# ─────────────────────────────────────────
# 9. TESTS MANUELS
# ─────────────────────────────────────────
print("\n" + "=" * 60)
print("🧪 TESTS MANUELS")
print("=" * 60)

jours_map   = {j: i for i, j in enumerate(le_jour.classes_)}
saisons_map = {s: i for i, s in enumerate(le_saison.classes_)}
types_map   = {t: i for i, t in enumerate(le_type.classes_)}

scenarios = [
    (8.5,  5,  "Lundi",    "Hiver",     "Urgence",                  8),
    (12.0, 0,  "Mercredi", "Été",       "Vaccination",               3),
    (17.0, 0,  "Vendredi", "Printemps", "Consultation générale",     5),
    (10.0, 0,  "Jeudi",    "Automne",   "Bilan de santé",           11),
    (14.5, 30, "Mardi",    "Hiver",     "Consultation de suivi",     2),
    (9.0,  15, "Samedi",   "Été",       "Autre",                     6),
]

for heure, minute, jour, saison, type_c, position in scenarios:
    mois = 1 if saison == "Hiver" else (4 if saison == "Printemps" else (7 if saison == "Été" else 10))
    X_manuel = pd.DataFrame([[
        heure, minute, mois,
        jours_map.get(jour, 0),
        saisons_map.get(saison, 0),
        types_map.get(type_c, 0)
    ]], columns=FEATURES)

    duree_predite     = model.predict(X_manuel)[0]
    temps_attente     = position * duree_predite
    heure_passage     = heure + (temps_attente / 60)
    h, m              = int(heure_passage), int((heure_passage % 1) * 60)

    print(f"  📍 {jour} {int(heure)}h{minute:02d} | {saison} | {type_c}")
    print(f"     Position {position} → {duree_predite:.1f} min/patient → Attente : {temps_attente:.0f} min → Passage : {h}h{m:02d}")
    print()

# ─────────────────────────────────────────
# 10. GRAPHIQUE PRÉDICTIONS VS RÉALITÉ
# ─────────────────────────────────────────
plt.figure(figsize=(8, 5))
plt.scatter(y_test, y_pred, alpha=0.4, color="steelblue", s=20)
plt.plot([0, 45], [0, 45], color="red", linestyle="--", label="Prédiction parfaite")
plt.xlabel("Durée réelle (min)")
plt.ylabel("Durée prédite (min)")
plt.title("Prédictions vs Réalité — Random Forest SmartWaiting")
plt.legend()
plt.tight_layout()
plt.savefig("data/predictions_vs_realite.png", dpi=150)
plt.show()

# ─────────────────────────────────────────
# 11. SAUVEGARDE
# ─────────────────────────────────────────
os.makedirs("models", exist_ok=True)
joblib.dump(model,      "models/model_smartwaiting.pkl")
joblib.dump(le_jour,    "models/le_jour.pkl")
joblib.dump(le_saison,  "models/le_saison.pkl")
joblib.dump(le_type,    "models/le_type.pkl")

# Sauvegarder aussi la liste des features pour l'API
import json
with open("models/features.json", "w", encoding="utf-8") as f:
    json.dump({
        "features"      : FEATURES,
        "types_valides" : list(le_type.classes_),
        "jours_valides" : list(le_jour.classes_),
        "saisons_valides": list(le_saison.classes_)
    }, f, ensure_ascii=False, indent=2)

print("✅ Modèle sauvegardé → models/model_smartwaiting.pkl")
print("✅ Encodeurs sauvegardés → models/le_jour/saison/type.pkl")
print("✅ Features sauvegardées → models/features.json")