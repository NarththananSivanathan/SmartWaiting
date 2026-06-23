JOURS_VALIDES  = {"Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi", "Dimanche"}
SAISONS_VALIDES = {"Hiver", "Printemps", "Été", "Automne"}


# ──────────────────────────────────────────────────────────────
# POST /start
# ──────────────────────────────────────────────────────────────

def test_start_consultation_champs_derives(client):
    """Les champs date, jour_semaine et saison_annee sont calculés automatiquement."""
    res = client.post("/api/consultations/start", json={"type_rdv": "Urgence"})
    assert res.status_code == 201
    data = res.json()
    assert data["type_rdv"] == "Urgence"
    assert data["jour_semaine"] in JOURS_VALIDES
    assert data["saison_annee"] in SAISONS_VALIDES
    assert data["heure_depart"] is None
    assert data["duree_consultation"] is None


def test_start_consultation_sans_type(client):
    """type_rdv est optionnel."""
    res = client.post("/api/consultations/start", json={})
    assert res.status_code == 201
    assert res.json()["type_rdv"] is None


# ──────────────────────────────────────────────────────────────
# PATCH /{id}/end
# ──────────────────────────────────────────────────────────────

def test_end_consultation(client):
    """Terminer une consultation calcule heure_depart et duree_consultation."""
    cid = client.post("/api/consultations/start", json={}).json()["id"]
    res = client.patch(f"/api/consultations/{cid}/end")
    assert res.status_code == 200
    data = res.json()
    assert data["heure_depart"] is not None
    assert data["duree_consultation"] is not None
    assert data["duree_consultation"] >= 0


def test_end_consultation_introuvable(client):
    res = client.patch("/api/consultations/99999/end")
    assert res.status_code == 404


def test_end_consultation_deja_terminee(client):
    """Terminer deux fois la même consultation renvoie 400."""
    cid = client.post("/api/consultations/start", json={}).json()["id"]
    client.patch(f"/api/consultations/{cid}/end")
    res = client.patch(f"/api/consultations/{cid}/end")
    assert res.status_code == 400


# ──────────────────────────────────────────────────────────────
# PATCH /{id}/type
# ──────────────────────────────────────────────────────────────

def test_set_type_rdv(client):
    cid = client.post("/api/consultations/start", json={}).json()["id"]
    res = client.patch(f"/api/consultations/{cid}/type", json={"type_rdv": "Vaccination"})
    assert res.status_code == 200
    assert res.json()["type_rdv"] == "Vaccination"


def test_set_type_rdv_introuvable(client):
    res = client.patch("/api/consultations/99999/type", json={"type_rdv": "Urgence"})
    assert res.status_code == 404


# ──────────────────────────────────────────────────────────────
# GET /
# ──────────────────────────────────────────────────────────────

def test_list_consultations_vide(client):
    res = client.get("/api/consultations/")
    assert res.status_code == 200
    data = res.json()
    assert data["total"] == 0
    assert data["data"] == []
    assert data["pages"] == 0


def test_list_consultations_pagination(client):
    for _ in range(5):
        client.post("/api/consultations/start", json={})
    res = client.get("/api/consultations/?page=1&size=3")
    assert res.status_code == 200
    data = res.json()
    assert data["total"] == 5
    assert len(data["data"]) == 3
    assert data["pages"] == 2


def test_list_consultations_page2(client):
    for _ in range(5):
        client.post("/api/consultations/start", json={})
    res = client.get("/api/consultations/?page=2&size=3")
    assert res.status_code == 200
    assert len(res.json()["data"]) == 2


# ──────────────────────────────────────────────────────────────
# GET /{id}
# ──────────────────────────────────────────────────────────────

def test_get_consultation(client):
    cid = client.post("/api/consultations/start", json={"type_rdv": "Bilan de santé"}).json()["id"]
    res = client.get(f"/api/consultations/{cid}")
    assert res.status_code == 200
    assert res.json()["type_rdv"] == "Bilan de santé"


def test_get_consultation_introuvable(client):
    res = client.get("/api/consultations/99999")
    assert res.status_code == 404


# ──────────────────────────────────────────────────────────────
# GET /stats
# ──────────────────────────────────────────────────────────────

def test_stats_base_vide(client):
    res = client.get("/api/consultations/stats")
    assert res.status_code == 200
    data = res.json()
    assert data["total_today"] == 0
    assert data["avg_duree_globale"] == 0.0
    assert data["duree_par_type"] == []


def test_stats_compte_aujourd_hui(client):
    client.post("/api/consultations/start", json={"type_rdv": "Urgence"})
    client.post("/api/consultations/start", json={"type_rdv": "Vaccination"})
    data = client.get("/api/consultations/stats").json()
    assert data["total_today"] == 2


def test_stats_duree_par_type(client, db):
    """Les durées moyennes par type sont correctement calculées."""
    from app.models import Consultation
    from datetime import datetime, date

    for type_rdv, duree in [("Urgence", 40), ("Urgence", 30), ("Vaccination", 12)]:
        db.add(Consultation(
            heure_arrivee=datetime.now(), heure_depart=datetime.now(),
            date=date.today(), duree_consultation=duree,
            jour_semaine="Lundi", saison_annee="Été", type_rdv=type_rdv,
        ))
    db.commit()

    data = client.get("/api/consultations/stats").json()
    types = {row["type_rdv"]: row for row in data["duree_par_type"]}

    assert "Urgence" in types
    assert "Vaccination" in types
    assert types["Urgence"]["nb"] == 2
    assert types["Vaccination"]["nb"] == 1
    assert types["Urgence"]["avg_duree"] == 35.0
    assert types["Vaccination"]["avg_duree"] == 12.0
