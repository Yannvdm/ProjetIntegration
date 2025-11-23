import matplotlib.patches as patches
import matplotlib.pyplot as plt
import constants as c


class EurobotField:
    def __init__(self):
        self.largeur = c.TABLE_LARGEUR
        self.profondeur = c.TABLE_PROFONDEUR

    def draw_static_elements(self, ax, image_path=None):
        """Dessine les éléments fixes du plateau sur le graphique ax"""

        # Configuration de l'affichage
        ax.set_xlim(-0, self.largeur + 0)
        ax.set_ylim(-0, self.profondeur + 0)
        ax.set_aspect('equal')

        table = patches.Rectangle((0, 0), self.largeur, self.profondeur,
                                  facecolor='grey', edgecolor='black',
                                  zorder=0)
        ax.add_patch(table)

        if image_path:
            try:
                img = plt.imread(image_path)
                ax.imshow(img, extent=[0, self.largeur, 0, self.profondeur],
                          zorder=0)
            except FileNotFoundError:
                print(f"Erreur : Image '{image_path}' introuvable.")

        # Le Grenier
        grenier_x = (self.largeur - c.GRENIER_LARGEUR) / 2
        grenier_y = self.profondeur - c.GRENIER_PROFONDEUR

        grenier = patches.Rectangle((grenier_x, grenier_y), c.GRENIER_LARGEUR,
                                    c.GRENIER_PROFONDEUR,
                                    facecolor=c.COLOR_GRENIER, hatch='//',
                                    label="Grenier", zorder=1)
        ax.add_patch(grenier)
