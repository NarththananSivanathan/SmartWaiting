import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import seaborn as sns

# ─────────────────────────────────────────
# CHARGEMENT
# ─────────────────────────────────────────
# Utilise le vrai fichier CSV si disponible, sinon le dataset généré
try:
    df = pd.read_csv("data/consultations.csv")
    print("📂 Fichier réel chargé : consultations.csv")
except FileNotFoundError:
    df = pd.read_csv("data/consultations_generated.csv")
    print("📂 Dataset généré chargé : consultations_generated.csv")

# ─────────────────────────────────────────
# PRÉ-TRAITEMENT
# ─────────────────────────────────────────
df["heure_arrivee"] = pd.to_datetime(df["heure_arrivee"])
df["heure_depart"]  = pd.to_datetime(df["heure_depart"])

# Filtrer les lignes avec durée nulle ou anormale (données incomplètes)
df = df[df["duree_consultation"] > 0].copy()

# Heure décimale (ex: 10h30 → 10.5)
df["heure_decimal"] = df["heure_arrivee"].dt.hour + df["heure_arrivee"].dt.minute / 60

# Tranche horaire
df["tranche"] = pd.cut(
    df["heure_decimal"],
    bins=[7, 9, 11, 13, 15, 17, 19],
    labels=["7h-9h", "9h-11h", "11h-13h", "13h-15h", "15h-17h", "17h-19h"]
)

print(f"✅ {len(df)} consultations valides chargées\n")

# ─────────────────────────────────────────
# FIGURE PRINCIPALE — 6 graphiques
# ─────────────────────────────────────────
sns.set_theme(style="darkgrid")
fig, axes = plt.subplots(3, 2, figsize=(16, 14))
fig.suptitle("📊 Analyse du Dataset — SmartWaiting", fontsize=16, fontweight="bold")

COULEURS_TYPES = {
    "Consultation générale" : "#4C8BE2",
    "Consultation de suivi" : "#5DADE2",
    "Vaccination"           : "#52BE80",
    "Urgence"               : "#E74C3C",
    "Bilan de santé"        : "#F39C12",
    "Autre"                 : "#9B59B6",
}

# ── G1 : Durée selon l'heure (nuage de points) ──────────────────────────────
ax = axes[0, 0]
for type_rdv, groupe in df.groupby("type_rdv"):
    ax.scatter(
        groupe["heure_decimal"], groupe["duree_consultation"],
        alpha=0.35, s=15, label=type_rdv,
        color=COULEURS_TYPES.get(type_rdv, "gray")
    )
ax.set_title("Durée de consultation selon l'heure d'arrivée")
ax.set_xlabel("Heure d'arrivée")
ax.set_ylabel("Durée (minutes)")
ax.legend(fontsize=7, loc="upper right")

# ── G2 : Durée moyenne par tranche horaire ──────────────────────────────────
ax = axes[0, 1]
moy_tranche = df.groupby("tranche", observed=True)["duree_consultation"].mean()
bars = ax.bar(moy_tranche.index, moy_tranche.values, color="#4C8BE2", edgecolor="white")
ax.set_title("Durée moyenne par tranche horaire")
ax.set_xlabel("Tranche horaire")
ax.set_ylabel("Durée moyenne (min)")
for bar, val in zip(bars, moy_tranche.values):
    ax.text(bar.get_x() + bar.get_width() / 2, val + 0.3,
            f"{val:.1f}", ha="center", fontweight="bold", fontsize=9)

# ── G3 : Durée moyenne par jour de la semaine ───────────────────────────────
ax = axes[1, 0]
ordre_jours = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi", "Dimanche"]
moy_jour = df.groupby("jour_semaine")["duree_consultation"].mean().reindex(ordre_jours).dropna()
bars = ax.bar(moy_jour.index, moy_jour.values, color="#E67E22", edgecolor="white")
ax.set_title("Durée moyenne par jour de la semaine")
ax.set_xlabel("Jour")
ax.set_ylabel("Durée moyenne (min)")
for bar, val in zip(bars, moy_jour.values):
    ax.text(bar.get_x() + bar.get_width() / 2, val + 0.3,
            f"{val:.1f}", ha="center", fontweight="bold", fontsize=9)

# ── G4 : Répartition des types de RDV (camembert) ───────────────────────────
ax = axes[1, 1]
counts = df["type_rdv"].value_counts()
couleurs_pie = [COULEURS_TYPES.get(t, "gray") for t in counts.index]
wedges, texts, autotexts = ax.pie(
    counts.values, labels=counts.index, autopct="%1.1f%%",
    colors=couleurs_pie, startangle=140,
    textprops={"fontsize": 8}
)
ax.set_title("Répartition des types de consultations")

# ── G5 : Distribution des durées ────────────────────────────────────────────
ax = axes[2, 0]
ax.hist(df["duree_consultation"], bins=30, color="#52BE80", edgecolor="white")
ax.set_title("Distribution des durées de consultation")
ax.set_xlabel("Durée (minutes)")
ax.set_ylabel("Nombre de consultations")
moy = df["duree_consultation"].mean()
med = df["duree_consultation"].median()
ax.axvline(moy, color="red",    linestyle="--", label=f"Moyenne : {moy:.1f} min")
ax.axvline(med, color="orange", linestyle=":",  label=f"Médiane : {med:.1f} min")
ax.legend()

# ── G6 : Durée moyenne par type et par saison (grouped bar) ─────────────────
ax = axes[2, 1]
pivot = df.pivot_table(
    index="type_rdv", columns="saison_annee",
    values="duree_consultation", aggfunc="mean"
)
pivot.plot(kind="bar", ax=ax, edgecolor="white", width=0.7)
ax.set_title("Durée moyenne par type de RDV et saison")
ax.set_xlabel("Type de consultation")
ax.set_ylabel("Durée moyenne (min)")
ax.tick_params(axis="x", rotation=25)
ax.legend(title="Saison", fontsize=8)

plt.tight_layout()
plt.savefig("data/visualisation_dataset.png", dpi=150, bbox_inches="tight")
plt.show()
print("✅ Graphiques générés → data/visualisation_dataset.png")