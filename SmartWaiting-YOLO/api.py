"""
API du service vision (IoT / camera)
========================================
Ce fichier transforme image_occupancy_sensor.py (un script en ligne de
commande) en un petit service web que le backend peut appeler par une
simple requete HTTP. C'est la "porte d'entree" de votre travail vu depuis
le reste de l'application.

NOTE SUR LES NOMS : la variable "app" reste en anglais car c'est une
convention imposee par FastAPI/uvicorn (la commande "uvicorn api:app"
cherche precisement une variable nommee "app"). Les cles du JSON renvoye
("occupied_count", "timestamp") restent aussi en anglais : c'est le
contrat de donnees partage avec le backend, deja documente.

Lancer en local (sans Docker, pour tester) :
    uvicorn api:app --host 0.0.0.0 --port 8001 --reload

Tester rapidement avec curl :
    curl -X POST -F "image=@salle1.jpg" http://localhost:8001/analyser

Le backend, lui, fera exactement la meme requete, juste depuis son propre
code (par exemple avec la librairie "requests" en Python, ou "fetch" en
JavaScript) plutot que depuis curl.
"""

from datetime import datetime, timezone
from functools import lru_cache

import numpy as np
import cv2
from fastapi import FastAPI, UploadFile, File, Depends

from image_occupancy_sensor import CapteurOccupationImage

app = FastAPI(title="Service vision - occupation salle d'attente")


@lru_cache
def obtenir_capteur() -> CapteurOccupationImage:
    """
    Cree le capteur (et charge le modele YOLO) UNE SEULE FOIS, au premier
    appel, puis reutilise toujours la meme instance. Charger un modele YOLO
    est lent (quelques secondes) : on ne veut pas refaire ça a chaque image
    recue, seulement au demarrage du service.
    """
    return CapteurOccupationImage()


@app.post("/analyser")
async def analyser_image(
    image: UploadFile = File(...),
    capteur: CapteurOccupationImage = Depends(obtenir_capteur),
):
    """
    Endpoint principal. Recoit une image (la photo - generee par IA ou non -
    simulant la camera de la salle d'attente) et retourne le nombre de
    places occupees detectees.

    Reponse JSON :
        {
            "occupied_count": 3,
            "timestamp": "2026-06-17T08:00:00+00:00"
        }
    """
    # 1. Lire les octets bruts du fichier envoye par le backend
    contenu = await image.read()

    # 2. Les convertir en image exploitable par OpenCV (meme format que
    #    cv2.imread, mais a partir de donnees en memoire plutot que d'un
    #    fichier sur disque - car ici l'image arrive via le reseau)
    tableau_octets = np.frombuffer(contenu, dtype=np.uint8)
    image_decodee = cv2.imdecode(tableau_octets, cv2.IMREAD_COLOR)

    # 3. Reutiliser exactement la meme logique de detection que le script
    #    en ligne de commande (occupancy_logic.py + yolo_detection.py)
    places_occupees, boites_personnes = capteur.analyser(image_decodee)

    # 4. Renvoyer un resultat simple, dans le meme "contrat de donnees"
    #    que les autres capteurs du projet (timestamp + occupied_count)
    return {
        "occupied_count": places_occupees,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/sante")
def verification_sante():
    """
    Endpoint de "health check". Ne fait rien de special, sert juste a
    verifier que le service est demarre et repond - tres utilise avec
    Docker pour savoir si un conteneur est pret.
    """
    return {"status": "ok"}
