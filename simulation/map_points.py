import constants as c


class Zone:
    def __init__(self, x_coin, y_coin, nom):
        # Coins en bas a gauche du rectangle/carre
        self.x_coin = x_coin
        self.y_coin = y_coin
        self.nom = nom

        self.largeur = 0
        self.profondeur = 0
        self.couleur = ''
        self.type = ''
        self.nb_caisses = 0
        self.max_caisses = 50

    @property
    def centre(self):
        return (self.x_coin + self.largeur / 2,
                self.y_coin + self.profondeur / 2)


class Nid(Zone):
    def __init__(self, x, y, nom, couleur):
        super().__init__(x, y, nom)
        self.largeur = c.START_ZONE_LARGEUR
        self.profondeur = c.START_ZONE_PROFONDEUR
        self.couleur = couleur
        self.type = 'nid'


class GardeManger(Zone):
    def __init__(self, x, y, nom):
        super().__init__(x, y, nom)
        self.largeur = self.profondeur = c.GARDE_MANGER_TAILLE
        self.couleur = 'green'
        self.type = 'gm'
        self.max_caisses = 4


class Ramassage(Zone):
    def __init__(self, x, y, nom):
        super().__init__(x, y, nom)
        self.largeur = c.ZONE_RAMASSAGE_LARGEUR
        self.profondeur = c.ZONE_RAMASSAGE_PROFONDEUR
        self.couleur = 'red'
        self.type = 'ramassage'
        self.nb_caisses = 4


def generer_graphe():
    zones = []
    zones.append(Nid(0, c.TABLE_PROFONDEUR - c.START_ZONE_PROFONDEUR,
                     "Nid Jaune", c.COLOR_YELLOW))
    zones.append(Nid(c.TABLE_LARGEUR - c.START_ZONE_LARGEUR,
                     c.TABLE_PROFONDEUR - c.START_ZONE_PROFONDEUR,
                     "Nid Bleu", c.COLOR_BLUE))

    zones.append(GardeManger(600, 0, "GM Bas 1"))
    zones.append(GardeManger(1400, 0, "GM Bas 2"))
    zones.append(GardeManger(2200, 0, "GM Bas 3"))

    zones.append(GardeManger(0, 700, "GM Mid 1"))
    zones.append(GardeManger(705, 700, "GM Mid 2"))
    zones.append(GardeManger(1400, 700, "GM Mid 3"))
    zones.append(GardeManger(2105, 700, "GM Mid 4"))
    zones.append(GardeManger(2800, 700, "GM Mid 5"))

    zones.append(GardeManger(1155, 1350, "GM Haut 1"))
    zones.append(GardeManger(1655, 1350, "GM Haut 2"))

    # vertical
    zones.append(Ramassage(100, 1100, "Ramasse gauche haut"))
    zones.append(Ramassage(100, 300, "Ramasse gauche bas"))
    zones.append(Ramassage(2750, 1100, "Ramasse droite haut"))
    zones.append(Ramassage(2750, 300, "Ramasse droite bas"))

    return zones
