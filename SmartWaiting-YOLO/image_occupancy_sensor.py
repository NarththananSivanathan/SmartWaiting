"""
Detection d'occupation a partir d'images statiques
========================================================
SCRIPT PRINCIPAL de votre partie du projet.

Concu pour le cas ou aucune vraie camera n'est disponible : les images
d'entree sont generees (par IA) pour simuler des photos de la salle
d'attente a differents moments. Le script analyse une image (ou un dossier
entier d'images) et produit le meme contrat de sortie que les autres
capteurs du projet : un CSV avec les colonnes (timestamp, occupied_count).
C'est ce CSV (ou l'equivalent via l'API, voir api.py) que le service ML de
votre collegue va consommer.

REGLE METIER SIMPLIFIEE : on ne cherche plus a savoir quelle chaise est
occupee (une chaise occupee est trop souvent masquee par la personne
assise dessus pour que YOLO la detecte fiablement, voir yolo_detection.py).
On suppose simplement que CHAQUE PERSONNE DETECTEE occupe une place. Le
nombre de places occupees = le nombre de personnes detectees, point.
C'est moins precis dans l'absolu (une personne debout serait comptee a
tort) mais beaucoup plus robuste en pratique.

Pre-requis (a installer sur la machine d'execution) :
    pip install ultralytics opencv-python-headless --break-system-packages

Usage - une seule image:
    python image_occupancy_sensor.py --image salle1.jpg --save-annotated salle1_annotee.jpg --csv occupation.csv

Usage - dossier d'images (traitees dans l'ordre alphabetique des noms de
fichiers, avec un horodatage simule qui avance de --interval-seconds a
chaque image - utile quand les images IA representent une sequence dans
le temps, par exemple "8h, 8h10, 8h20..."):
    python image_occupancy_sensor.py --folder images/ --csv occupation_images.csv \\
        --start-time 2026-06-17T08:00:00 --interval-seconds 600 --annotated-dir annotees/
"""

import argparse
import csv
import os
import glob
from datetime import datetime, timedelta, timezone

import cv2  # OpenCV : librairie de traitement d'image (lecture, ecriture, dessin)

from occupancy_logic import compter_places_occupees
from yolo_detection import detecter_personnes


class CapteurOccupationImage:
    """
    Classe principale : regroupe le modele YOLO et les parametres de
    detection. On cree UNE instance de cette classe, puis on l'utilise
    pour analyser autant d'images que l'on veut (le modele n'est charge
    qu'une seule fois, a la creation : c'est l'etape la plus lente).
    """

    def __init__(self, modele=None, chemin_modele="yolov8n.pt", confiance=0.4):
        """
        Le "constructeur" : code execute automatiquement quand on ecrit
        CapteurOccupationImage(...). Il prepare le modele a etre utilise.

        modele        : permet d'injecter un modele DEJA charge (utilise
                        uniquement dans les tests, pour simuler YOLO sans
                        avoir besoin de le telecharger - voir
                        test_image_occupancy_integration.py)
        chemin_modele : sinon, chemin/nom du modele YOLO pre-entraine a
                        charger automatiquement (telecharge la premiere
                        fois si absent du disque)
        confiance     : seuil de confiance minimal pour garder une
                        detection (personne ou siege)
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
        Analyse une image deja chargee en memoire (tableau numpy).
        Retourne (places_occupees, boites_personnes) :
            - places_occupees  : nombre de personnes detectees, considere
                                  comme le nombre de places occupees (voir
                                  la regle metier en haut du fichier)
            - boites_personnes : la liste des boites de personnes detectees,
                                  utile pour dessiner l'image annotee ensuite
        """
        boites_personnes = detecter_personnes(self.modele, image, confiance=self.confiance)
        places_occupees = compter_places_occupees(boites_personnes)
        return places_occupees, boites_personnes

    def analyser_fichier(self, chemin_image):
        """
        Meme chose que analyser(), mais a partir d'un CHEMIN de fichier sur
        le disque plutot que d'une image deja en memoire. Pratique pour
        analyser un fichier .jpg/.png directement.
        """
        image = cv2.imread(chemin_image)
        if image is None:
            # cv2.imread ne leve pas d'erreur si le fichier n'existe pas ou
            # n'est pas une image valide : il retourne juste "None". On
            # verifie nous-memes pour donner un message d'erreur clair.
            raise ValueError(f"Impossible de lire l'image : {chemin_image}")
        return self.analyser(image), image


def annoter(image, boites_personnes):
    """
    Dessine une boite bleue sur chaque personne detectee, sur une COPIE de
    l'image (on ne modifie jamais l'originale) : chaque personne est
    consideree comme occupant une place. Tres utile pour deboguer si les
    resultats semblent bizarres, en particulier avec des images generees
    par IA (style different des photos reelles sur lesquelles YOLO a ete
    entraine a l'origine).
    """
    image_annotee = image.copy()  # .copy() : sinon on dessinerait sur l'originale

    for boite_personne in boites_personnes:
        x1, y1, x2, y2 = [int(v) for v in boite_personne]  # cv2 a besoin d'entiers, pas de floats
        # Couleur au format BGR (Bleu-Vert-Rouge, l'ordre utilise par OpenCV
        # - attention, c'est l'INVERSE du RGB plus habituel)
        cv2.rectangle(image_annotee, (x1, y1), (x2, y2), (220, 130, 0), 2)
        cv2.putText(image_annotee, "occupee", (x1, max(0, y1 - 6)), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (220, 130, 0), 2)

    return image_annotee


def ajouter_ligne_csv(chemin_csv, horodatage, nombre_occupees):
    """
    Ajoute une ligne (horodatage, nombre_occupees) a la fin d'un fichier CSV.
    Si le fichier n'existe pas encore (ou est vide), on ecrit d'abord la
    ligne d'en-tete avec les noms de colonnes (qui restent en anglais,
    "timestamp"/"occupied_count" : c'est le contrat de donnees partage
    avec le service ML).
    """
    fichier_existe = os.path.exists(chemin_csv) and os.path.getsize(chemin_csv) > 0
    # mode "a" = "append" = on ajoute a la fin du fichier sans effacer ce
    # qui existait deja (different de "w" = "write" qui efface tout)
    with open(chemin_csv, "a", newline="") as f:
        redacteur_csv = csv.writer(f)
        if not fichier_existe:
            redacteur_csv.writerow(["timestamp", "occupied_count"])
        redacteur_csv.writerow([horodatage, nombre_occupees])


def traiter_image_unique(capteur, chemin_image, chemin_annotee=None, chemin_csv=None, horodatage=None):
    """
    Traite UNE image de bout en bout : analyse, affichage du resultat,
    sauvegarde de l'image annotee (si demande) et ecriture dans le CSV
    (si demande). C'est la fonction appelee aussi bien par le mode
    "--image" que par traiter_dossier() ci-dessous pour chaque image du lot.
    """
    (places_occupees, boites_personnes), image = capteur.analyser_fichier(chemin_image)
    print(f"{chemin_image} -> places occupees = {places_occupees}")

    if chemin_annotee:
        image_annotee = annoter(image, boites_personnes)
        cv2.imwrite(chemin_annotee, image_annotee)
        print(f"Image annotee sauvegardee -> {chemin_annotee}")

    if chemin_csv:
        # Si on n'a pas precise d'horodatage explicite, on utilise l'heure
        # actuelle (utile en mode "--image" tout seul, sans dossier).
        horodatage_final = horodatage or datetime.now(timezone.utc).isoformat()
        ajouter_ligne_csv(chemin_csv, horodatage_final, places_occupees)

    return places_occupees


def traiter_dossier(capteur, dossier, chemin_csv, heure_debut=None, intervalle_secondes=60, dossier_annotees=None):
    """
    Traite TOUTES les images d'un dossier, dans l'ordre alphabetique de
    leurs noms de fichiers, et leur attribue un horodatage qui avance
    progressivement (heure_debut, puis +intervalle_secondes a chaque image).

    Exemple concret : si vos images generees par IA s'appellent
    "salle_08h00.jpg", "salle_08h10.jpg", "salle_08h20.jpg"... l'ordre
    alphabetique correspond deja a l'ordre chronologique, donc il suffit de
    leur donner --start-time 08:00 et --interval-seconds 600 (10 minutes)
    pour reconstituer la bonne chronologie dans le CSV final.
    """
    # glob.glob() cherche tous les fichiers qui correspondent a un motif
    # (ici, toutes les extensions d'image courantes). On combine plusieurs
    # motifs avec une "list comprehension" imbriquee : pour chaque extension,
    # pour chaque fichier trouve, on garde son chemin. sorted() les remet
    # ensuite dans l'ordre alphabetique.
    extensions = ("*.jpg", "*.jpeg", "*.png", "*.bmp")
    chemins_images = sorted(
        p for ext in extensions for p in glob.glob(os.path.join(dossier, ext))
    )
    if not chemins_images:
        print(f"Aucune image trouvee dans {dossier}")
        return

    # "or" ici sert de valeur par defaut : si heure_debut est None (pas
    # precise par l'utilisateur), on prend l'heure actuelle a la place.
    heure_courante = heure_debut or datetime.now(timezone.utc)

    if dossier_annotees:
        os.makedirs(dossier_annotees, exist_ok=True)  # cree le dossier s'il n'existe pas deja

    # On recree le CSV pour CE traitement (mode "w" = on efface l'ancien
    # contenu s'il y en avait, pour repartir d'un fichier propre a chaque
    # lancement du traitement par lot).
    with open(chemin_csv, "w", newline="") as f:
        csv.writer(f).writerow(["timestamp", "occupied_count"])

    for chemin_image in chemins_images:
        chemin_annotee = None
        if dossier_annotees:
            nom_fichier = os.path.basename(chemin_image)  # juste le nom du fichier, sans le dossier
            chemin_annotee = os.path.join(dossier_annotees, f"annotee_{nom_fichier}")

        traiter_image_unique(
            capteur, chemin_image,
            chemin_annotee=chemin_annotee,
            chemin_csv=chemin_csv,
            horodatage=heure_courante.isoformat(),
        )
        # On avance l'horloge simulee pour la prochaine image du dossier
        heure_courante += timedelta(seconds=intervalle_secondes)

    print(f"\n{len(chemins_images)} images traitees -> {chemin_csv}")


def main():
    """
    Point d'entree du script en ligne de commande : lit les options passees
    apres "python image_occupancy_sensor.py", puis appelle la bonne fonction
    selon que l'utilisateur a demande "--image" (une seule photo) ou
    "--folder" (un dossier entier).
    """
    analyseur = argparse.ArgumentParser(description="Detection d'occupation a partir d'images statiques")
    analyseur.add_argument("--image", type=str, help="Chemin d'une image unique a analyser")
    analyseur.add_argument("--folder", type=str, help="Dossier contenant plusieurs images a traiter en lot")
    analyseur.add_argument("--model", type=str, default="yolov8n.pt")
    analyseur.add_argument("--conf", type=float, default=0.4, help="Seuil de confiance des detections")
    analyseur.add_argument("--save-annotated", type=str, default=None, help="(mode image unique) chemin de l'image annotee de sortie")
    analyseur.add_argument("--annotated-dir", type=str, default=None, help="(mode dossier) dossier de sortie des images annotees")
    analyseur.add_argument("--csv", type=str, default="occupation_images.csv")
    analyseur.add_argument("--start-time", type=str, default=None, help="Horodatage ISO de depart pour le mode dossier (defaut: maintenant)")
    analyseur.add_argument("--interval-seconds", type=float, default=60.0, help="Ecart de temps simule entre deux images du dossier")
    arguments = analyseur.parse_args()

    if not arguments.image and not arguments.folder:
        analyseur.error("Precise --image (une photo) ou --folder (un dossier de photos)")

    capteur = CapteurOccupationImage(chemin_modele=arguments.model, confiance=arguments.conf)

    if arguments.image:
        traiter_image_unique(capteur, arguments.image, chemin_annotee=arguments.save_annotated, chemin_csv=arguments.csv)

    if arguments.folder:
        # datetime.fromisoformat() convertit une chaine de texte type
        # "2026-06-17T08:00:00" en un vrai objet date/heure manipulable
        heure_debut = datetime.fromisoformat(arguments.start_time) if arguments.start_time else None
        traiter_dossier(
            capteur, arguments.folder, chemin_csv=arguments.csv,
            heure_debut=heure_debut, intervalle_secondes=arguments.interval_seconds,
            dossier_annotees=arguments.annotated_dir,
        )


# Cette condition est une convention standard en Python : le code a
# l'interieur ne s'execute QUE si on lance ce fichier directement
# (python image_occupancy_sensor.py), pas si on l'importe depuis un autre
# fichier (comme le fait api.py, qui a juste besoin de la classe
# CapteurOccupationImage, sans vouloir relancer tout le programme).
if __name__ == "__main__":
    main()
