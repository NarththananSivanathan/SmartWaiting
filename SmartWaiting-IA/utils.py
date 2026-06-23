JOURS_FR = {
    0: "Lundi", 1: "Mardi", 2: "Mercredi",
    3: "Jeudi", 4: "Vendredi", 5: "Samedi", 6: "Dimanche",
}


def get_saison(mois: int) -> str:
    if mois in [12, 1, 2]: return "Hiver"
    if mois in [3, 4, 5]:  return "Printemps"
    if mois in [6, 7, 8]:  return "Été"
    return "Automne"