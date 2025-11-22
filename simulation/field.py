import matplotlib.patches as patches
import matplotlib.pyplot as plt
import constants as c


class EurobotField:
    def __init__(self):
        self.longueur = c.TABLE_LONGUEUR
        self.largeur = c.TABLE_LARGEUR

    def draw_static_elements(self, ax, image_path=None):
        """Dessine les éléments fixes du plateau sur le graphique ax"""

        # Configuration de l'affichage
        ax.set_xlim(-200, self.longueur + 200)
        ax.set_ylim(-200, self.largeur + 200)
        ax.set_aspect('equal')

        table = patches.Rectangle((0, 0), self.longueur, self.largeur,
                                  facecolor=c.COLOR_FLOOR, edgecolor='black',
                                  zorder=0)
        ax.add_patch(table)

        if image_path:
            try:
                img = plt.imread(image_path)
                ax.imshow(img, extent=[0, self.longueur, 0, self.largeur],
                          zorder=0)
            except FileNotFoundError:
                print(f"Erreur : Image '{image_path}' introuvable.")

        # Zone de départ JAUNE (Haut Gauche)
        start_jaune = patches.Rectangle((0,
                                        self.largeur - c.START_ZONE_LARGEUR),
                                        c.START_ZONE_LONGUEUR,
                                        c.START_ZONE_LARGEUR,
                                        color=c.COLOR_YELLOW, alpha=0.3,
                                        label="Départ jaune")
        ax.add_patch(start_jaune)

        # Zone de départ BLEU (Haut Droite)
        start_bleu = patches.Rectangle((self.longueur - c.START_ZONE_LONGUEUR,
                                        self.largeur - c.START_ZONE_LARGEUR),
                                       c.START_ZONE_LONGUEUR,
                                       c.START_ZONE_LARGEUR,
                                       color=c.COLOR_BLUE, alpha=0.3,
                                       label="Départ Bleu")
        ax.add_patch(start_bleu)

        # Le Grenier
        # Centré en X : (3000 - 1800) / 2 = 600
        grenier_x = (self.longueur - c.GRENIER_LONGUEUR) / 2
        grenier_y = self.largeur - c.GRENIER_LARGEUR

        grenier = patches.Rectangle((grenier_x, grenier_y), c.GRENIER_LONGUEUR,
                                    c.GRENIER_LARGEUR,
                                    facecolor=c.COLOR_GRENIER, hatch='//',
                                    label="Grenier", zorder=1)
        ax.add_patch(grenier)
