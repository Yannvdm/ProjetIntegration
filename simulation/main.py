# main.py
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from field import EurobotField
import map_points
import os


def run_visualization():
    fig, ax = plt.subplots(figsize=(12, 8))

    dossier_courant = os.path.dirname(os.path.abspath(__file__))
    chemin_image = os.path.join(dossier_courant, "map_eurobot.png")

    terrain = EurobotField()
    terrain.draw_static_elements(ax, image_path=chemin_image)

    # Génération des zones  
    reseau = map_points.generer_graphe()
    print("Simulation lancée.")

    for zone in reseau:
        rect = patches.Rectangle((zone.x_coin, zone.y_coin), 
                                 zone.largeur, zone.profondeur,
                                 linewidth=0,
                                 edgecolor='none',
                                 facecolor=zone.couleur,
                                 alpha=0.2,
                                 zorder=10)
        ax.add_patch(rect)

    plt.title("Eurobot 2026 - Simulation")
    plt.grid(True, linestyle=':', alpha=0.4)
    plt.xlabel("X (mm)")
    plt.ylabel("Y (mm)")

    # Force l'aspect ratio pour ne pas déformer le terrain
    ax.set_aspect('equal', adjustable='box')

    plt.show()


if __name__ == "__main__":
    run_visualization()
