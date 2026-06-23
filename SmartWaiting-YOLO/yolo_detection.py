"""
Wrapper autour d'un modele de detection (type ultralytics YOLO)
====================================================================
Ce fichier fait le lien entre "un modele YOLO charge en memoire" et "une
liste de boites Python simples" que le reste du code sait manipuler. C'est
le SEUL endroit du projet ou on lit directement le format de sortie propre
a la librairie ultralytics : si un jour vous changez de modele ou de
version, c'est ici (et nulle part ailleurs) qu'il faudra adapter le code.

Il est utilise a l'identique par camera_occupancy_sensor.py (flux video) et
image_occupancy_sensor.py (images statiques), pour garantir que la
detection se comporte exactement de la meme facon dans les deux cas.

Rappel sur YOLO : c'est un modele d'intelligence artificielle deja entraine
sur des millions d'images (jeu de donnees "COCO"), qui sait reconnaitre 80
types d'objets du quotidien, dont "person" (personne). On ne le reentraine
pas : on l'utilise "tel quel" (on dit qu'on fait de l'inference, pas de
l'entrainement).

On ne detecte QUE les personnes ici (pas les chaises) : le nombre de
places occupees est calcule a partir du nombre de personnes detectees,
considerees comme assises (voir image_occupancy_sensor.py). Detecter les
chaises elles-memes s'est avere peu fiable (une chaise occupee est en
grande partie cachee par la personne assise dessus), donc on s'en passe.

NOTE SUR LES NOMS : "person" reste en anglais ci-dessous car c'est le nom
EXACT impose par le modele YOLO lui-meme (jeu de donnees COCO) - ce n'est
pas un choix de notre part, on ne peut pas le traduire.
"""

ETIQUETTE_PERSONNE = "person"


def detecter_personnes(modele, image, confiance=0.4):
    """
    Execute le modele YOLO sur une image et en extrait uniquement les
    boites de PERSONNES detectees (tout le reste - chaises, chiens,
    telephones... - est ignore).

    Parametres :
        modele    : l'objet modele deja charge (ultralytics.YOLO(...))
        image     : l'image a analyser, sous forme de tableau numpy
                    (c'est le format que renvoie cv2.imread() ou cv2.VideoCapture)
        confiance : seuil de confiance entre 0 et 1. En dessous de ce
                    seuil, on considere que la detection n'est pas fiable
                    et on l'ignore. 0.4 = on garde seulement les
                    detections dont le modele est sur a au moins 40%.

    Retourne : boites_personnes, une liste de boites au format [x1, y1, x2, y2]
    """
    # Appeler le modele comme une fonction (modele(...)) lance la detection.
    # Le resultat est une liste (on prend le premier element [0] car on
    # n'analyse qu'une seule image a la fois, pas un lot de plusieurs).
    # NOTE : "conf=" et "verbose=" ci-dessous sont les noms de parametres
    # imposes par la librairie ultralytics elle-meme (pas les notres).
    # verbose=False : on demande au modele de ne pas afficher ses propres
    # logs internes dans la console, pour ne pas polluer nos messages.
    resultats = modele(image, conf=confiance, verbose=False)[0]

    # resultats.names est un dictionnaire qui traduit un numero de classe
    # (ex: 0) en son nom lisible (ex: "person"). Ce mapping est fourni par
    # le modele lui-meme (attribut impose par ultralytics).
    noms = resultats.names

    boites_personnes = []

    # resultats.boxes contient une entree par objet detecte dans l'image
    # (attribut impose par ultralytics). On parcourt chaque detection une
    # par une.
    for boite in resultats.boxes:
        # boite.cls[0] est le numero de la classe detectee (ex: 0 pour "person").
        # int(...) convertit ce nombre (qui arrive sous forme de tensor
        # PyTorch) en entier Python classique, pour pouvoir l'utiliser comme
        # cle dans le dictionnaire "noms".
        etiquette = noms[int(boite.cls[0])]

        if etiquette != ETIQUETTE_PERSONNE:
            # Pas une personne (une chaise, un chien...) : on ignore.
            continue

        # boite.xyxy[0] contient les 4 coordonnees [x1, y1, x2, y2] de la
        # boite, toujours sous forme de tensor PyTorch. .tolist() les
        # convertit en une liste Python normale, plus facile a manipuler
        # ensuite. (hasattr verifie juste que la methode existe : ca permet
        # a ce code de fonctionner aussi avec de fausses donnees de test qui
        # n'ont pas cette methode, voir test_yolo_detection.py)
        coordonnees = boite.xyxy[0]
        coordonnees = coordonnees.tolist() if hasattr(coordonnees, "tolist") else list(coordonnees)
        boites_personnes.append(coordonnees)

    return boites_personnes
