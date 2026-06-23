import pandas as pd
import numpy as np
import os
from datetime import datetime, timedelta, date

# ─────────────────────────────────────────────────────────────────────────────
# CONFIGURATION
# ─────────────────────────────────────────────────────────────────────────────
np.random.seed(42)
NB_CONSULTATIONS = 1500   # volume suffisant pour entraîner un bon modèle

TYPES_RDV = [
    "Consultation générale",
    "Consultation de suivi",
    "Vaccination",
    "Urgence",
    "Bilan de santé",
    "Autre",
]

# Probabilité d'apparition de chaque type (réaliste pour un cabinet de médecine générale)
PROBA_TYPES = [0.28, 0.22, 0.16, 0.12, 0.12, 0.10]

# Jours d'ouverture (le cabinet est fermé le dimanche)
JOURS_OUVERTS = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi"]
# Samedi = demi-journée → flux spécifique géré dans la logique horaire

SAISONS = ["Hiver", "Printemps", "Été", "Automne"]

# Mois associés à chaque saison (pour les timestamps)
MOIS_PAR_SAISON = {
    "Hiver"    : [12, 1, 2],
    "Printemps": [3, 4, 5],
    "Été"      : [6, 7, 8],
    "Automne"  : [9, 10, 11],
}

# ─────────────────────────────────────────────────────────────────────────────
# LOGIQUE MÉTIER RÉALISTE
# Les durées sont calibrées sur la pratique réelle de médecine générale :
#   - Renouvellement / vaccination / suivi simple   : 10–20 min
#   - Consultation classique / bilan               : 20–35 min
#   - Urgence / bilan complet                      : 30–45 min
# ─────────────────────────────────────────────────────────────────────────────

# Base de durée (en minutes) par type de consultation
DUREE_BASE = {
    "Consultation générale" : (22, 5),   # (mu, sigma)
    "Consultation de suivi" : (15, 3),
    "Vaccination"           : (12, 2),
    "Urgence"               : (35, 6),
    "Bilan de santé"        : (32, 5),
    "Autre"                 : (18, 4),
}

def duree_consultation(heure: float, jour: str, saison: str, type_rdv: str) -> int:
    """
    Génère une durée de consultation réaliste (en minutes entières).
    Les effets sont additifs et calibrés pour créer un signal clair
    sans variance excessive.
    """
    mu, sigma = DUREE_BASE[type_rdv]
    duree = np.random.normal(mu, sigma)

    # ── Effet de l'heure ──────────────────────────────────────────────────────
    # Début de journée : le médecin est frais, les patients souvent complexes
    # Fin de matinée   : flux rapide, consultations courtes (salle pleine)
    # Après-midi       : rythme ralenti, cas plus longs
    # Fin de journée   : consultations expédiées, patients pressés
    if 8.0 <= heure < 9.5:
        duree += 3    # premiers RDV souvent plus longs (anamnèse complète)
    elif 9.5 <= heure < 11.0:
        duree += 0    # rythme de croisière
    elif 11.0 <= heure < 12.5:
        duree -= 3    # accélération avant la pause déjeuner
    elif 12.5 <= heure < 14.0:
        duree += 1    # reprise après-midi, quelques urgences de midi
    elif 14.0 <= heure < 16.0:
        duree += 2    # après-midi chargé, cas complexes reportés du matin
    elif 16.0 <= heure < 17.5:
        duree -= 1    # cadence stable
    else:             # 17h30–19h
        duree -= 4    # dernières consultations : médecin fatigue, patients pressés

    # ── Effet du jour ─────────────────────────────────────────────────────────
    if jour == "Lundi":
        duree += 4    # accumulation du week-end (pathologies non prises en charge)
    elif jour == "Mardi":
        duree += 1
    elif jour == "Mercredi":
        duree -= 1    # flux régulier, journée calme dans beaucoup de cabinets
    elif jour == "Vendredi":
        duree += 2    # patients qui veulent régler les problèmes avant le week-end
    elif jour == "Samedi":
        duree += 5    # urgences de dernière minute, médecin de garde souvent

    # ── Effet de la saison ───────────────────────────────────────────────────
    if saison == "Hiver":
        duree += 4    # grippe, bronchites, gastros → consultations plus longues
    elif saison == "Printemps":
        duree += 0    # saison neutre
    elif saison == "Été":
        duree -= 3    # moins de pathologies lourdes, souvent renouvellements
    elif saison == "Automne":
        duree += 2    # reprise des maladies saisonnières

    return int(round(max(5, min(45, duree))))


def heure_arrivee_realiste(jour: str, saison: str) -> float:
    """
    Génère une heure d'arrivée réaliste (décimale) selon le profil du jour.
    Les cabinets ouvrent généralement à 8h et ferment à 19h (samedi : 8h-13h).
    La distribution est bimodale (pic matin + pic après-midi).
    """
    if jour == "Samedi":
        # Samedi : seulement le matin, forte densité entre 8h et 12h30
        heure = np.random.choice(
            [np.random.uniform(8.0, 12.5), np.random.uniform(8.0, 10.5)],
            p=[0.6, 0.4]
        )
        return round(min(heure, 12.5), 4)

    # Semaine : bimodal — pic matin (8h–12h) et pic après-midi (14h–18h30)
    segment = np.random.choice(["matin", "apres_midi"], p=[0.55, 0.45])
    if segment == "matin":
        # Légèrement concentré vers 9h–11h (plein rendement)
        heure = np.random.triangular(8.0, 10.0, 12.5)
    else:
        # Concentré vers 15h–17h
        heure = np.random.triangular(13.5, 15.5, 19.0)

    return round(heure, 4)


def saison_depuis_mois(mois: int) -> str:
    if mois in [12, 1, 2]:  return "Hiver"
    elif mois in [3, 4, 5]: return "Printemps"
    elif mois in [6, 7, 8]: return "Été"
    else:                    return "Automne"


def jour_depuis_date(d: date) -> str:
    jours = ["Lundi","Mardi","Mercredi","Jeudi","Vendredi","Samedi","Dimanche"]
    return jours[d.weekday()]


# ─────────────────────────────────────────────────────────────────────────────
# GÉNÉRATION DES ENREGISTREMENTS
# ─────────────────────────────────────────────────────────────────────────────
records = []
start_id = 1001

# Plage de dates : une année complète (2025)
all_dates = pd.date_range("2025-01-01", "2025-12-31", freq="D")
# Filtrer les dimanches (cabinet fermé)
dates_ouvertes = [d for d in all_dates if d.weekday() != 6]  # 0=lundi … 5=samedi

for i in range(NB_CONSULTATIONS):
    # Tirage d'une date aléatoire parmi les jours ouvrables
    ts_date  = pd.Timestamp(np.random.choice(dates_ouvertes))
    d        = ts_date.date()
    jour     = jour_depuis_date(d)
    mois     = d.month
    saison   = saison_depuis_mois(mois)

    # Heure d'arrivée réaliste selon le jour
    heure_decimal = heure_arrivee_realiste(jour, saison)
    h_arr = int(heure_decimal)
    m_arr = int((heure_decimal % 1) * 60)
    sec_arr = np.random.randint(0, 60)

    # Type de consultation (légèrement modulé par le moment de la journée)
    # Les urgences sont plus fréquentes en début et fin de journée
    if heure_decimal < 9.0 or heure_decimal > 17.5:
        proba_locale = [0.20, 0.18, 0.14, 0.22, 0.14, 0.12]
    else:
        proba_locale = PROBA_TYPES
    type_rdv = np.random.choice(TYPES_RDV, p=proba_locale)

    # Durée calculée selon la logique métier
    duree = duree_consultation(heure_decimal, jour, saison, type_rdv)

    # Construction des timestamps
    arrivee = datetime(d.year, d.month, d.day, h_arr, m_arr, sec_arr)
    depart  = arrivee + timedelta(minutes=duree)

    records.append({
        "id"                : start_id + i,
        "heure_arrivee"     : arrivee.strftime("%Y-%m-%d %H:%M:%S"),
        "heure_depart"      : depart.strftime("%Y-%m-%d %H:%M:%S"),
        "date"              : str(d),
        "duree_consultation": duree,
        "jour_semaine"      : jour,
        "saison_annee"      : saison,
        "type_rdv"          : type_rdv,
    })

df = pd.DataFrame(records)

# ─────────────────────────────────────────────────────────────────────────────
# SAUVEGARDE
# ─────────────────────────────────────────────────────────────────────────────
os.makedirs("data", exist_ok=True)
df.to_csv("data/consultations.csv", index=False)

# ─────────────────────────────────────────────────────────────────────────────
# RAPPORT DE VALIDATION
# ─────────────────────────────────────────────────────────────────────────────
print(f"✅ Dataset généré : {len(df)} consultations → data/consultations.csv\n")

print("📊 Aperçu (5 premières lignes) :")
print(df.head(5).to_string(index=False))

print("\n📈 Statistiques globales sur la durée (minutes) :")
print(df["duree_consultation"].describe().round(1).to_string())

print("\n📋 Durée moyenne par type de RDV :")
print(df.groupby("type_rdv")["duree_consultation"]
        .agg(["mean","std","min","max"])
        .round(1)
        .sort_values("mean", ascending=False)
        .to_string())

print("\n📅 Durée moyenne par jour :")
ordre = ["Lundi","Mardi","Mercredi","Jeudi","Vendredi","Samedi"]
print(df.groupby("jour_semaine")["duree_consultation"]
        .mean().reindex(ordre).round(1).to_string())

print("\n🌍 Durée moyenne par saison :")
print(df.groupby("saison_annee")["duree_consultation"]
        .mean().round(1).to_string())

print("\n⏰ Durée moyenne par tranche horaire :")
df["heure_decimal"] = pd.to_datetime(df["heure_arrivee"]).dt.hour + \
                      pd.to_datetime(df["heure_arrivee"]).dt.minute / 60
df["tranche"] = pd.cut(df["heure_decimal"],
                        bins=[7,9,11,13,15,17,19],
                        labels=["7h-9h","9h-11h","11h-13h","13h-15h","15h-17h","17h-19h"])
print(df.groupby("tranche", observed=True)["duree_consultation"].mean().round(1).to_string())