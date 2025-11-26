import matplotlib.patches as patches
import matplotlib.transforms as transforms
import numpy as np


class Robot:
    def __init__(self, x, y, theta=0, color='black'):
        self.x = x
        self.y = y
        self.theta = theta
        self.largeur = 300
        self.longueur = 300
        self.color = color

    def draw(self, ax):
        rect = patches.Rectangle(
            (-self.largeur / 2, -self.longueur / 2),
            self.largeur,
            self.longueur,
            facecolor='white',
            edgecolor=self.color,
            linewidth=2,
            zorder=20
        )

        t = transforms.Affine2D().rotate_deg(self.theta).translate(self.x,
                                                                   self.y)
        rect.set_transform(t + ax.transData)
        ax.add_patch(rect)

        arrow_len = self.longueur / 2
        rad = np.deg2rad(self.theta)
        end_x = self.x + arrow_len * np.cos(rad)
        end_y = self.y + arrow_len * np.sin(rad)

        ax.arrow(
            self.x, self.y,
            end_x - self.x, end_y - self.y,
            head_width=30,
            head_length=30,
            fc='red',
            ec='red',
            zorder=21
        )
