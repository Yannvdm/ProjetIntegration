import matplotlib.pyplot as plt
import matplotlib.patches as patches
from field import EurobotField
import map_points
import robot
import os
import time
import random
import datetime
import json
import dataclasses
import tkinter as tk
from menu import Launcher


def save_match_history(score, config):
    filename = "matches.json"

    # 1. On convertit la config (DataClass) en dictionnaire simple
    config_dict = dataclasses.asdict(config)

    # 2. On prépare l'entrée pour l'historique
    new_entry = {
        "date": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "score": score,
        "robot_color": config.color,
        "config": config_dict
    }

    # 3. On charge l'existant ou on crée une liste vide
    history = []
    if os.path.exists(filename):
        try:
            with open(filename, "r") as f:
                history = json.load(f)
        except:
            history = []  # Si fichier corrompu, on repart à zéro

    # 4. On ajoute et on sauvegarde
    history.append(new_entry)

    with open(filename, "w") as f:
        json.dump(history, f, indent=4)

    print(f"--> Résultat sauvegardé dans {filename} (Total parties: {len(history)})")


def calculate_action_duration(base_time, noise, prob_fail, fail_penalty):
    duration = base_time + random.uniform(0, noise)
    if duration < 0.1: duration = 0.1 # Minimum physique

    # Test d'échec
    if random.uniform(0, 100) < prob_fail:
        print(f"  fail (+{fail_penalty}s)")
        duration += fail_penalty

    return duration


def calculate_score(zones, team_color):
    """
    Calcule le score actuel.
    Pour l'instant (démo solo), on compte tout ce qui est dans les GM + le Nid de la couleur du robot.
    """
    score = 0
    target_nid_name = "Nid Bleu" if team_color == "blue" else "Nid Jaune"
    nb_caisses_nid = 0
    nb_caisse_gm = 0

    for z in zones:
        if z.nb_caisses > 0:
            if z.type == 'nid' and z.nom == target_nid_name:
                score += z.nb_caisses * 1  # 1 point par caisse au nid
                nb_caisses_nid += z.nb_caisses

            elif z.type == 'gm':
                score += z.nb_caisses * 3  # 3 points par caisse en GM (bonus)
                nb_caisse_gm += z.nb_caisses

    return score, nb_caisses_nid, nb_caisse_gm


def run_visualization():
    # 1. Config
    root = tk.Tk()
    app = Launcher(root)
    root.mainloop() 
    config = app.cfg_blue

    # 2. Graphique
    plt.ion()
    fig, ax = plt.subplots(figsize=(10, 7))
    dossier = os.path.dirname(os.path.abspath(__file__))
    terrain = EurobotField()
    terrain.draw_static_elements(ax, image_path=os.path.join(dossier, "map_eurobot.png"))

    zones = map_points.generer_graphe()

    # Initialisation de l'affichage des zones et des compteurs
    compteurs_visuels = {}
    for z in zones:
        coul = z.couleur if z.couleur else 'gray'
        rect = patches.Rectangle((z.x_coin, z.y_coin), z.largeur, z.profondeur,
                                 lw=1, ec='white', fc=coul, alpha=0.3)
        ax.add_patch(rect)

        # On affiche un compteur sur TOUTES les zones (0 pour Nids/GM, 4 pour Ramassage)
        cx, cy = z.centre
        txt = ax.text(cx, cy, str(z.nb_caisses),
                      color='white', fontsize=12, fontweight='bold',
                      ha='center', va='center', zorder=30)
        compteurs_visuels[z.nom] = txt

    # 3. Robot
    bot = robot.Robot(x=2800, y=1800, theta=180, color='blue',
                      speed=config.speed, speed_noise=config.speed_noise, capacity=config.capacity)
    bot.draw(ax)

    # --- VARIABLES DE SIMULATION ---
    MATCH_DURATION = 90
    current_time = 0.0
    last_time = time.time()

    state = "CHERCHE CAISSE"
    target_zone = None
    action_end_time = 0.2
    fini = False
    while current_time < MATCH_DURATION:

        # --- MACHINE A ETATS ---
        now = time.time()
        dt = now - last_time
        last_time = now
        if dt > 0.1: 
            dt = 0.1

        if state == "CHERCHE CAISSE":
            # On cherche la zone de ramassage la plus proche avec du stock
            target_pickup = bot.get_nearest_pickup_with_stock(zones)

            if target_pickup:
                print(f"[{current_time:.1f}s] Nouvelle cible : {target_pickup.nom}")
                target_zone = target_pickup
                state = "VERS CAISSE"
            else:
                print("Plus aucune caisse sur la table !")
                state = "FINISHED"

        elif state == "VERS CAISSE":
            tx, ty = target_zone.centre
            arrived = bot.move_to(tx, ty, dt)
            if arrived:
                # Calcul du temps de prise (Simulation)
                duration = calculate_action_duration(config.t_pick, config.t_pick_noise, 
                                                  config.prob_pick_fail, config.time_pick_fail)
                action_end_time = current_time + duration
                print(f"[{current_time:.1f}s] Prise en cours... ({duration:.1f}s) sacchant que ça pouvait etre {config.t_pick} +{config.t_pick_noise}")
                state = "RAMASSAGE"

        elif state == "RAMASSAGE":
            # Le robot ne bouge pas, il ramasse
            if current_time >= action_end_time:
                # Action terminée
                target_zone.nb_caisses -= 1
                bot.stock += 1
                compteurs_visuels[target_zone.nom].set_text(str(target_zone.nb_caisses))

                if bot.stock < bot.capacity:
                    state = "CHERCHE CAISSE"
                else:   
                    # Décision de la destination (Nid vs GM)
                    destination = bot.decide_strategy(zones, config.risk)
                    if destination:
                        target_zone = destination
                        state = "VERS DEPOT"
                    else:
                        state = "FINISHED"  # Normalement pas mdr

        elif state == "VERS DEPOT":
            tx, ty = target_zone.centre
            arrived = bot.move_to(tx, ty, dt)
            if arrived:
                # Calcul du temps de dépose
                duration = calculate_action_duration(config.t_drop, config.t_drop_noise, 
                                                  config.prob_drop_fail, config.time_drop_fail)
                action_end_time = current_time + duration

                print(f"[{current_time:.1f}s] Dépose en cours... ({duration:.1f}s)")
                state = "DROP"

        elif state == "DROP":
            if current_time >= action_end_time:
                # Action terminée
                target_zone.nb_caisses += 1
                bot.stock -= 1
                compteurs_visuels[target_zone.nom].set_text(str(target_zone.nb_caisses))
                print(f"[{current_time:.1f}s] Caisse déposée dans {target_zone.nom}.")

                if bot.stock == 0 or target_zone.nb_caisses >= target_zone.max_caisses:
                    state = "CHERCHE CAISSE"
                else:
                    duration = calculate_action_duration(config.t_drop, config.t_drop_noise, 
                                              config.prob_drop_fail, config.time_drop_fail)
                    action_end_time = current_time + duration
                    state = "DROP"

        elif state == "FINISHED":
            pass  # On attend la fin du match

        bot.update_graphics(ax)
        current_time += dt
        current_score = calculate_score(zones, bot.color) 
        if current_time < MATCH_DURATION:
            ax.set_title(f"Temps: {MATCH_DURATION - current_time:.1f}s | État: {state} | Score Bleu: {current_score[0]} (Nid: {current_score[1]}, GM: {current_score[2]})",)
        else:
            fini = True


        plt.draw()
        plt.pause(0.001)

        if not plt.fignum_exists(fig.number):
            break
    ax.set_title(f"FINI | Score Bleu: {current_score[0]} (Nid: {current_score[1]}, GM: {current_score[2]})",)

    plt.ioff()
    plt.close()
    if fini:
        final_score = calculate_score(zones, bot.color)
        print("\n=== FIN DU MATCH ===")
        print(f"Score Final : {final_score}")
        save_match_history(final_score, config)


if __name__ == "__main__":
    run_visualization()
