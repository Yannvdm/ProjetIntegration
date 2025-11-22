# map_points.py
import constants as c


class Node:
    def __init__(self, x, y, nom, type_node, caisses=0):
        self.x = x
        self.y = y
        self.nom = nom
        self.type = type_node
        self.caisses = caisses

    def get_pos(self):
        return (self.x, self.y)


def generer_graphe():
    """Retourne une liste de Node représentant les points d'intérêt"""
    nodes = []

    # Nid Bleu
    x_bleu = c.START_ZONE_LARGEUR / 2
    y_bleu = c.TABLE_LARGEUR - (c.START_ZONE_LONGUEUR / 2)
    nodes.append(Node(x_bleu, y_bleu, "Nid Bleu", "nid", caisses=0))

    # Nid Jaune
    x_jaune = c.TABLE_LONGUEUR - (c.START_ZONE_LARGEUR / 2)
    y_jaune = c.TABLE_LARGEUR - (c.START_ZONE_LONGUEUR / 2)
    nodes.append(Node(x_jaune, y_jaune, "Nid Jaune", "nid", caisses=0))

    y_haut = 1200
    y_bas = 800
    colonnes = [700, 1500, 2300]

    compteur = 1
    for x in colonnes:
        nodes.append(Node(x, y_haut, f"GM Haut {compteur}", "pantry",
                          caisses=2))
        nodes.append(Node(x, y_bas, f"GM Bas {compteur}", "pantry", caisses=2))
        compteur += 1

    return nodes
