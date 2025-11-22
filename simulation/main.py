import matplotlib.pyplot as plt
from field import EurobotField
import map_points


def run_visualization():
    fig, ax = plt.subplots(figsize=(12, 8))

    terrain = EurobotField()
    terrain.draw_static_elements(ax, image_path="simulation/map_eurobot.png")
    reseau = map_points.generer_graphe()
    print(f"Simulation chargée avec {len(reseau)} points d'intérêt.")

    for node in reseau:
        if node.type == 'pantry':
            couleur = 'red'
            taille = 150
        else:
            couleur = 'blue'
            taille = 200

        ax.scatter(node.x, node.y, s=taille, c=couleur, zorder=10,
                   edgecolors='white')

        ax.text(node.x + 40, node.y + 40, node.nom,
                fontsize=9, fontweight='bold', color='black', zorder=11,
                bbox=dict(facecolor='white', alpha=0.7, edgecolor='none',
                          pad=1))

    plt.title("Eurobot 2026 - Carte Stratégique (Nœuds)")
    plt.grid(True, linestyle='--', alpha=0.5)
    plt.xlabel("X (mm)")
    plt.ylabel("Y (mm)")
    plt.show()


if __name__ == "__main__":
    run_visualization()
