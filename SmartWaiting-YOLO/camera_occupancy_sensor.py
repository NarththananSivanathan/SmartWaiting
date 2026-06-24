"""
Capteur d'occupation par camera (YOLO)
==========================================
Variante de image_occupancy_sensor.py pour un flux camera EN DIRECT
(webcam ou fichier video) plutot que des images statiques. Conserve a
titre de reference au cas ou une vraie camera deviendrait disponible plus
tard - ce n'est pas le script que vous utilisez au quotidien.

REGLE METIER (la meme que pour les images statiques) : on ne cherche pas
a detecter precisement les chaises (une chaise occupee est trop souvent
masquee par la personne assise dessus pour que YOLO la detecte fiablement).
On suppose simplement que CHAQUE PERSONNE DETECTEE occupe une place. Le
nombre de places occupees = le nombre de personnes detectees, point.

NOTE SUR LES NOMS : les options en ligne de commande (--source, --model,
--conf, --interval, --duration, --csv, --show) et les noms de colonnes du
CSV (timestamp, occupied_count) restent volontairement en anglais : c'est
le "contrat" deja documente et partage avec le reste de l'equipe. Seuls
les noms de variables et de fonctions internes au code sont traduits en
francais.

Pre-requis (a installer sur la machine qui execute ce script, avec acces
internet pour le premier telechargement du modele) :
    pip install ultralytics opencv-python --break-system-packages

Usage:
    python camera_occupancy_sensor.py --source 0 --interval 1 --csv occupation.csv
    python camera_occupancy_sensor.py --source video.mp4 --show
"""

import argparse
import csv
import json
import time
import urllib.request
from datetime import datetime, timezone

from occupancy_logic import compter_places_occupees
from yolo_detection import detecter_personnes


def _envoyer_au_backend(backend_url, places_occupees):
    """
    Envoie le nombre de places occupees au backend SmartWaiting via HTTP POST.
    Utilise uniquement la bibliotheque standard (urllib) pour eviter
    d'ajouter une dependance supplementaire (requests, httpx...).
    Les erreurs sont loguees mais ne font pas planter la boucle principale.
    """
    payload = json.dumps({
        "occupied_chairs": places_occupees,
        "source": "camera",
    }).encode("utf-8")
    url = f"{backend_url.rstrip('/')}/api/occupancy/"
    req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=5):
            pass
    except Exception as e:
        print(f"[backend] Erreur lors de l'envoi : {e}")


class CapteurOccupationCamera:
    """
    Classe principale : regroupe le modele YOLO et le parametre de
    detection. On cree UNE instance de cette classe, puis on l'utilise
    pour analyser un flux video complet (le modele n'est charge qu'une
    seule fois, a la creation : c'est l'etape la plus lente).
    """

    def __init__(self, modele=None, chemin_modele="yolov8n.pt", confiance=0.4):
        """
        Le "constructeur" : code execute automatiquement quand on ecrit
        CapteurOccupationCamera(...). Il prepare le modele a etre utilise.

        modele        : permet d'injecter un modele DEJA charge (utilise
                        uniquement dans les tests, pour simuler YOLO sans
                        avoir besoin de le telecharger - voir
                        test_camera_occupancy_integration.py)
        chemin_modele : sinon, chemin/nom du modele YOLO pre-entraine a
                        charger automatiquement (telecharge la premiere
                        fois si absent du disque)
        confiance     : seuil de confiance minimal pour garder une detection
        """
        if modele is not None:
            self.modele = modele
        else:
            # L'import est fait ICI (et non en haut du fichier) volontairement :
            # ainsi, si on utilise un faux modele via le parametre "modele"
            # (dans les tests), on n'a meme pas besoin que la librairie
            # ultralytics soit installee.
            from ultralytics import YOLO
            self.modele = YOLO(chemin_modele)
        self.confiance = confiance

    def analyser(self, image):
        """
        Analyse une image (une "frame" de la video) deja chargee en
        memoire. Retourne (places_occupees, boites_personnes), exactement
        comme la methode equivalente de CapteurOccupationImage dans
        image_occupancy_sensor.py, pour garder une API coherente entre
        les deux capteurs.
        """
        boites_personnes = detecter_personnes(self.modele, image, confiance=self.confiance)
        places_occupees = compter_places_occupees(boites_personnes)
        return places_occupees, boites_personnes

    def stream(self, capture_video, intervalle=1.0, duree=None, chemin_csv=None, afficher=False, backend_url=None):
        """
        Boucle de capture + detection en continu, image par image.

        capture_video : objet avec une methode .read() -> (ok, image),
                        comme cv2.VideoCapture (injectable pour les tests,
                        voir test_camera_occupancy_integration.py)
        intervalle    : secondes entre deux detections
        duree         : duree totale en secondes (None = infini, jusqu'a
                        Ctrl+C ou fin du flux video)
        chemin_csv    : fichier CSV de sortie (memes colonnes que les
                        autres capteurs du projet)
        afficher      : afficher une fenetre video (necessite un
                        environnement graphique, ne fonctionne pas sur un
                        serveur sans ecran)
        backend_url   : URL du backend SmartWaiting (ex: http://localhost:8000)
                        Si fournie, chaque detection est envoyee via POST
                        a {backend_url}/api/occupancy/ en plus du CSV.
        """
        redacteur_csv = None
        fichier_csv = None
        if chemin_csv:
            fichier_csv = open(chemin_csv, "a", newline="")
            redacteur_csv = csv.writer(fichier_csv)
            if fichier_csv.tell() == 0:
                redacteur_csv.writerow(["timestamp", "occupied_count"])

        # cv2 (OpenCV) n'est importe ici que si on doit reellement afficher
        # une fenetre : ca evite d'en avoir besoin pour les tests qui ne
        # passent jamais afficher=True.
        cv2 = None
        if afficher:
            import cv2 as module_cv2
            cv2 = module_cv2

        debut = time.time()
        try:
            # Boucle principale : tant que la duree maximale n'est pas
            # atteinte (ou indefiniment si duree=None)...
            while duree is None or (time.time() - debut) < duree:
                ok, image = capture_video.read()
                if not ok:
                    # Plus d'image disponible (fin de la video, camera
                    # deconnectee...) : on arrete proprement la boucle.
                    print("Flux video indisponible, arret.")
                    break

                places_occupees, _ = self.analyser(image)
                horodatage = datetime.now(timezone.utc).isoformat()
                print(f"{horodatage} | places occupees = {places_occupees}")

                if redacteur_csv:
                    redacteur_csv.writerow([horodatage, places_occupees])
                    fichier_csv.flush()

                if backend_url:
                    _envoyer_au_backend(backend_url, places_occupees)

                if afficher and cv2:
                    cv2.imshow("Camera occupancy", image)
                    # Permet de fermer la fenetre proprement en appuyant sur "q"
                    if cv2.waitKey(1) & 0xFF == ord("q"):
                        break

                time.sleep(intervalle)
        except KeyboardInterrupt:
            # Permet d'arreter le script avec Ctrl+C sans message d'erreur moche
            print("\nDetection arretee.")
        finally:
            # Le bloc "finally" s'execute TOUJOURS, meme en cas d'erreur ou
            # de Ctrl+C : on s'assure que le fichier et la fenetre video
            # sont bien refermes proprement dans tous les cas.
            if fichier_csv:
                fichier_csv.close()
            if afficher and cv2:
                cv2.destroyAllWindows()


def main():
    """
    Point d'entree du script en ligne de commande : lit les options
    passees apres "python camera_occupancy_sensor.py", ouvre le flux
    video demande, puis lance la boucle de detection en continu.
    """
    analyseur = argparse.ArgumentParser(description="Capteur d'occupation par camera (YOLO)")
    analyseur.add_argument("--source", type=str, default="0", help="Index camera (0,1,...) ou chemin video/image")
    analyseur.add_argument("--model", type=str, default="yolov8n.pt", help="Modele YOLO pre-entraine")
    analyseur.add_argument("--conf", type=float, default=0.4, help="Seuil de confiance des detections")
    analyseur.add_argument("--interval", type=float, default=1.0, help="Intervalle entre detections (s)")
    analyseur.add_argument("--duration", type=float, default=None, help="Duree totale (s), infini si non precise")
    analyseur.add_argument("--csv", type=str, default="occupation_camera.csv", help="Fichier CSV de sortie")
    analyseur.add_argument("--show", action="store_true", help="Afficher la fenetre video annotee")
    analyseur.add_argument("--backend-url", type=str, default=None,
                           help="URL du backend SmartWaiting (ex: http://localhost:8000) pour envoyer les resultats en temps reel")
    arguments = analyseur.parse_args()

    import cv2

    # --source peut etre soit un numero de camera ("0", "1"...), soit un
    # chemin de fichier video ("video.mp4"). isdigit() permet de
    # distinguer les deux cas et de convertir en entier seulement si besoin.
    source = int(arguments.source) if arguments.source.isdigit() else arguments.source
    capture_video = cv2.VideoCapture(source)

    capteur = CapteurOccupationCamera(chemin_modele=arguments.model, confiance=arguments.conf)
    capteur.stream(
        capture_video,
        intervalle=arguments.interval,
        duree=arguments.duration,
        chemin_csv=arguments.csv,
        afficher=arguments.show,
        backend_url=arguments.backend_url,
    )
    capture_video.release()


# Cette condition est une convention standard en Python : le code a
# l'interieur ne s'execute QUE si on lance ce fichier directement
# (python camera_occupancy_sensor.py), pas si on l'importe depuis un
# autre fichier.
if __name__ == "__main__":
    main()
