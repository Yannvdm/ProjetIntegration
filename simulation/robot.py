import matplotlib.patches as patches
import matplotlib.transforms as transforms
import math
import random


class Robot:
    def __init__(self, x, y, theta=0, color='black', speed=300, speed_noise=0, capacity=4):
        self.x = x
        self.y = y
        self.theta = theta
        self.largeur = 300
        self.longueur = 300
        self.capacity = capacity
        self.color = color
        self.stock = 0
        self.base_speed = speed 
        self.speed_noise = speed_noise  # Incertitude vitesse

        self.patch_rect = None

    def draw(self, ax):
        self.patch_rect = patches.Rectangle(
            (-self.largeur / 2, -self.longueur / 2),
            self.largeur, self.longueur,
            facecolor='white', edgecolor=self.color, linewidth=2, zorder=20
        )

        ax.add_patch(self.patch_rect)

        self.text_stock = ax.text(self.x, self.y, str(self.stock),
                                  color='black',
                                  fontsize=14, fontweight='bold',
                                  ha='center', va='center', zorder=30)
        self.update_graphics(ax)

    def update_graphics(self, ax):
        t = transforms.Affine2D().rotate_deg(self.theta).translate(self.x, self.y)
        self.patch_rect.set_transform(t + ax.transData)
        if self.text_stock:
            # 1. On déplace le texte à la nouvelle position du robot
            self.text_stock.set_position((self.x, self.y))

            # 2. On met à jour le chiffre
            self.text_stock.set_text(f"{self.stock}/{self.capacity}")

    def move_to(self, target_x, target_y, dt):
        """Avance vers la cible avec vitesse variable (bruit)."""
        dx = target_x - self.x
        dy = target_y - self.y
        dist = math.hypot(dx, dy)

        if dist < 10: return True

        target_theta = math.degrees(math.atan2(dy, dx))
        self.theta = target_theta

        # Application du bruit sur la vitesse
        current_speed = self.base_speed + random.uniform(-self.speed_noise, self.speed_noise)
        if current_speed < 0: current_speed = 0  # Pas de marche arrière accidentelle

        step = current_speed * dt
        if step > dist: step = dist

        self.x += step * math.cos(math.radians(self.theta))
        self.y += step * math.sin(math.radians(self.theta))

        return False

    def decide_strategy(self, zones, risk_percent):
        """Décide Nid vs Garde-Manger."""
        tirage = random.uniform(0, 100)
        print(f"tirage = {tirage} vs risk = {risk_percent}")
        # Si audace (tirage < risk), on va au GM le plus proche
        if tirage <= risk_percent:
            return self.get_nearest_zone(zones, 'gm')
        else:
            # Sécurité : Retour au Nid
            target_color = "Bleu" if self.color == "blue" else "Jaune"
            for z in zones:
                if z.type == 'nid' and target_color in z.nom:
                    return z
        return None

    def get_nearest_zone(self, zones, type_filter):
        """Trouve la zone du type donné la plus proche."""
        min_dist = float('inf')
        nearest = None
        for z in zones:
            if z.type == type_filter and z.nb_caisses < z.max_caisses:
                zx, zy = z.centre
                d = math.hypot(zx - self.x, zy - self.y)
                if d < min_dist:
                    min_dist = d
                    nearest = z
        return nearest

    def get_nearest_pickup_with_stock(self, zones):
        """Cherche la zone de ramassage la plus proche QUI A ENCORE DES CAISSES."""
        min_dist = float('inf')
        nearest = None
        for z in zones:
            if z.type == 'ramassage' and z.nb_caisses > 0:
                zx, zy = z.centre
                d = math.hypot(zx - self.x, zy - self.y)
                if d < min_dist:
                    min_dist = d
                    nearest = z
        return nearest
