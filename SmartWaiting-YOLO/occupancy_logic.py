"""
Logique de detection d'occupation des chaises a partir de boites englobantes
================================================================================
Ce module ne contient QUE de la geometrie : il prend des "boites englobantes"
(en anglais "bounding boxes", ou "boxes") qui representent des rectangles
detectes dans une image, et il calcule si une chaise est occupee ou non.

Il ne depend ni de YOLO, ni d'OpenCV, ni d'une camera : c'est fait
volontairement, pour pouvoir le tester facilement sans avoir besoin d'un modele d'IA ou d'une image.

Une "boite englobante" est juste une liste de 4 nombres : [x1, y1, x2, y2]
    - (x1, y1) = coin haut-gauche du rectangle
    - (x2, y2) = coin bas-droite du rectangle
C'est le format standard utilise par la plupart des modeles de detection
d'objets, dont YOLO.

REGLE METIER : une chaise est consideree "occupee" si une personne detectee :
    - a son centre situe a l'interieur de la boite de la chaise, OU
    - a un recouvrement (IoU, explique plus bas) suffisant avec la chaise
"""


def calculer_iou(boite_a, boite_b):
    """
    Calcule l'IoU (Intersection over Union) entre deux boites.

    L'IoU est une mesure tres utilisee en vision par ordinateur pour savoir
    a quel point deux rectangles se recouvrent : 0 = aucun recouvrement,
    1 = les deux rectangles sont identiques.
    Formule : IoU = (aire de l'intersection) / (aire de l'union)

    boite_a, boite_b : listes [x1, y1, x2, y2]
    """
    # --- Etape 1 : calculer le rectangle d'INTERSECTION (la zone commune) ---
    # Le coin haut-gauche de l'intersection est le MAX des deux coins haut-gauche
    xa = max(boite_a[0], boite_b[0])
    ya = max(boite_a[1], boite_b[1])
    # Le coin bas-droite de l'intersection est le MIN des deux coins bas-droite
    xb = min(boite_a[2], boite_b[2])
    yb = min(boite_a[3], boite_b[3])

    # Largeur/hauteur de l'intersection. On utilise max(0, ...) car si les
    # boites ne se touchent pas du tout, (xb - xa) ou (yb - ya) seraient
    # negatifs : dans ce cas, l'intersection doit valoir 0, pas un nombre negatif.
    largeur_inter = max(0.0, xb - xa)
    hauteur_inter = max(0.0, yb - ya)
    aire_inter = largeur_inter * hauteur_inter  # aire = largeur x hauteur

    # --- Etape 2 : calculer l'aire de chaque boite individuellement ---
    aire_a = max(0.0, boite_a[2] - boite_a[0]) * max(0.0, boite_a[3] - boite_a[1])
    aire_b = max(0.0, boite_b[2] - boite_b[0]) * max(0.0, boite_b[3] - boite_b[1])

    # --- Etape 3 : aire de l'UNION = somme des deux aires moins l'intersection ---
    # (sinon on compterait deux fois la partie commune)
    union = aire_a + aire_b - aire_inter

    if union <= 0:
        # Cas limite : boites de taille nulle. On evite une division par zero.
        return 0.0
    return aire_inter / union


def point_dans_boite(point, boite):
    """
    Teste si un point (x, y) se trouve a l'interieur d'un rectangle [x1, y1, x2, y2].
    On compare simplement les coordonnees : le point doit etre apres le coin
    haut-gauche ET avant le coin bas-droite, sur les deux axes.
    """
    x, y = point  # "deballe" le tuple (x, y) dans deux variables separees
    return boite[0] <= x <= boite[2] and boite[1] <= y <= boite[3]


def chaise_est_occupee(boite_chaise, boites_personnes, seuil_iou=0.1):
    """
    Determine si UNE chaise donnee est occupee, en la comparant a TOUTES
    les personnes detectees dans l'image.

    Parametres :
        boite_chaise     : la boite de la chaise a tester, [x1, y1, x2, y2]
        boites_personnes : liste de boites de personnes detectees, ex :
                            [[10, 10, 40, 90], [50, 5, 80, 95]]
        seuil_iou         : seuil de recouvrement minimal (entre 0 et 1) pour
                            considerer que la personne est "sur" la chaise,
                            meme si son centre n'est pas exactement dedans
                            (utile si la personne est vue de cote, ou
                            partiellement masquee par une autre)

    On teste chaque personne une par une (boucle "for"). Des qu'UNE seule
    personne valide la condition d'occupation, on peut repondre tout de
    suite "True" et arreter la boucle (instruction "return" : elle sort
    immediatement de la fonction). Si on arrive a la fin de la boucle sans
    avoir trouve de personne correspondante, la chaise est vide -> False.
    """
    for boite_personne in boites_personnes:
        # Le "centre" d'une boite est la moyenne de ses coins opposes
        centre = (
            (boite_personne[0] + boite_personne[2]) / 2,
            (boite_personne[1] + boite_personne[3]) / 2,
        )

        # Premier test, le plus simple : le centre de la personne est-il
        # geometriquement a l'interieur de la chaise ?
        if point_dans_boite(centre, boite_chaise):
            return True

        # Deuxieme test, complementaire : meme si le centre n'est pas
        # exactement dans la chaise, un fort recouvrement (IoU) suffit aussi
        if calculer_iou(boite_chaise, boite_personne) >= seuil_iou:
            return True

    # Aucune personne n'a valide les conditions -> la chaise est vide
    return False


def compter_places_occupees(boites_personnes):
    """
    Calcule le nombre de places occupees a partir du nombre de PERSONNES
    detectees, pas du nombre de chaises detectees comme occupees.

    POURQUOI CE CHANGEMENT D'APPROCHE : une chaise occupee est en grande
    partie masquee par la personne assise dessus, donc YOLO la detecte
    souvent mal, voire pas du tout (voir yolo_detection.py). Essayer de
    faire correspondre chaque personne a une chaise precise (avec
    chaise_est_occupee/compter_chaises_occupees ci-dessus) echoue donc
    frequemment, non pas a cause d'une erreur de calcul, mais parce que la
    chaise elle-meme n'a jamais ete detectee au depart.

    On simplifie avec une hypothese volontaire : toute personne detectee
    dans la salle d'attente est consideree comme assise, donc occupant une
    place - qu'une chaise ait ete detectee sous elle ou non. C'est moins
    precis dans l'absolu (une personne debout serait comptee a tort), mais
    bien plus robuste en pratique, car la detection de personnes est
    nettement plus fiable que celle des chaises partiellement cachees.
    """
    return len(boites_personnes)
