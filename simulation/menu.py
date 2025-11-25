import tkinter as tk
from tkinter import ttk
from dataclasses import dataclass


@dataclass
class RobotConfig:
    color: str
    risk: int = 50
    aggro: int = 0
    # Locomotion
    speed: float = 300.0
    speed_noise: float = 50.0
    prob_move_fail: float = 5.0
    time_move_fail: float = 5.0
    # Prise objet
    t_pick: float = 2.0
    t_pick_noise: float = 0.5
    prob_pick_fail: float = 10.0
    time_pick_fail: float = 3.0
    # Dépose objet
    t_drop: float = 2.0
    t_drop_noise: float = 0.5
    prob_drop_fail: float = 5.0
    time_drop_fail: float = 2.0


class Launcher:
    def __init__(self, root):
        self.root = root
        self.root.title("Eurobot 2026 - Configuration")
        self.root.geometry("900x650")

        # Style général
        style = ttk.Style()
        style.theme_use('clam')  # Theme plus plat et moderne
        style.configure("TLabel", background="white", font=("Segoe UI", 9))
        style.configure("TButton", font=("Segoe UI", 10, "bold"), padding=10)
        style.configure("Header.TLabel", font=("Segoe UI", 12, "bold"))
        style.configure("Card.TFrame", background="white", relief="flat")

        # Conteneur principal
        main_container = tk.Frame(root, bg="#f0f0f0")
        main_container.pack(fill="both", expand=True)

        # Configs
        self.cfg_blue = RobotConfig("blue")
        self.cfg_yellow = RobotConfig("yellow")

        # --- Colonne BLEUE ---
        self.vars_b = self.create_column(main_container,
                                         "ÉQUIPE BLEUE",
                                         "#E3F2FD", "#1565C0", 0)

        # --- Colonne JAUNE ---
        self.vars_y = self.create_column(main_container,
                                         "ÉQUIPE JAUNE", "#FFFDE7",
                                         "#F9A825", 1)

        # --- Bouton Lancer ---
        btn_frame = tk.Frame(root, bg="#f0f0f0", pady=15)
        btn_frame.pack(fill="x", side="bottom")

        btn = tk.Button(btn_frame,
                        text="LANCER LA SIMULATION", command=self.run,
                        bg="#4CAF50", fg="white", font=("Segoe UI", 12,
                                                        "bold"),
                        relief="flat", cursor="hand2", padx=20, pady=10)
        btn.pack()

    def create_column(self, parent, title, bg_color, title_color, col_index):
        # Frame colorée pour la colonne
        col_frame = tk.Frame(parent, bg=bg_color)
        col_frame.pack(side="left", fill="both",
                       expand=True, padx=(0 if col_index == 0 else 2))

        # Titre de la colonne
        lbl_title = tk.Label(col_frame, text=title,
                             bg=bg_color, fg=title_color,
                             font=("Segoe UI", 16, "bold"), pady=15)
        lbl_title.pack(fill="x")

        vars = {}

        # 1. Carte Stratégie
        card_strat = self.create_card(col_frame,
                                      "STRATÉGIE & COMPORTEMENT")
        vars['risk'] = self.create_slider(card_strat,
                                          "Stratégie (Risque)", 50,
                                          "Sécurité", "Garde-Manger")
        vars['aggro'] = self.create_slider(card_strat,
                                           "Agressivité", 0, "Passif",
                                           "Voleur")

        # 2. Carte Locomotion
        card_loco = self.create_card(col_frame, "LOCOMOTION")
        self.create_row_entry(card_loco,
                              "Vitesse Cible (mm/s)", vars, 'speed', 300)
        self.create_row_entry(card_loco,
                              "Incertitude Vitesse (-mm/s)",
                              vars, 'speed_noise', 20)

        ttk.Separator(card_loco, orient="horizontal").pack(fill="x", pady=10)
        self.create_row_entry(card_loco,
                              "Probabilité fail (%)", vars, 'p_move', 2.0)
        self.create_row_entry(card_loco,
                              "Temps perdu fail (s)", vars, 't_move_lost',
                              5.0)

        # 3. Carte Actions
        card_act = self.create_card(col_frame, "ACTIONS (Prise / Pose)")
        # En-têtes tableau
        h_frame = tk.Frame(card_act, bg="white")
        h_frame.pack(fill="x", pady=(0, 5))
        headers = ["Act.", "Base(s)", "+Bruit(s)", "Fail(%)", "+Pen(s)"]
        widths = [8, 8, 8, 8, 8]
        for i, h in enumerate(headers):
            tk.Label(h_frame, text=h, bg="white", fg="#666",
                     font=("Segoe UI", 8,
                           "bold"), width=widths[i]).pack(side="left")

        # Lignes tableau
        self.create_action_row(card_act, "Prise", vars, 't_pick',
                               'noise_pick', 'p_pick',
                               'pen_pick', 2.0, 0.5, 10.0, 3.0)
        self.create_action_row(card_act, "Pose", vars, 't_drop',
                               'noise_drop', 'p_drop',
                               'pen_drop', 2.0, 0.5, 5.0, 2.0)

        return vars

    def create_card(self, parent, title):
        # Une "Carte" est un frame blanc avec un titre et du padding
        card = ttk.Frame(parent, style="Card.TFrame", padding=15)
        card.pack(fill="x", padx=15, pady=8)

        lbl = ttk.Label(card, text=title, style="Header.TLabel",
                        foreground="#333")
        lbl.pack(anchor="w", pady=(0, 10))
        return card

    def create_slider(self, parent, label, default, txt_left, txt_right):
        # Slider propre avec labels aux extrémités
        f = tk.Frame(parent, bg="white")
        f.pack(fill="x", pady=5)

        top = tk.Frame(f, bg="white")
        top.pack(fill="x")
        tk.Label(top, text=label, bg="white",
                 font=("Segoe UI", 9, "bold")).pack(side="left")
        val_lbl = tk.Label(top, text=f"{default}%", bg="#eee", width=4,
                           font=("Consolas", 9))
        val_lbl.pack(side="right")

        var = tk.IntVar(value=default)
        def upd(v): val_lbl.config(text=f"{int(float(v))}%")

        scale = ttk.Scale(f, from_=0, to=100, variable=var, command=upd)
        scale.pack(fill="x", pady=(2, 0))
        bot = tk.Frame(f, bg="white")
        bot.pack(fill="x")
        tk.Label(bot, text=txt_left, bg="white", fg="#888",
                 font=("Segoe UI", 7)).pack(side="left")
        tk.Label(bot, text=txt_right, bg="white", fg="#888",
                 font=("Segoe UI", 7)).pack(side="right")

        return var

    def create_row_entry(self, parent, label, vars_dict, key, default):
        f = tk.Frame(parent, bg="white")
        f.pack(fill="x", pady=2)
        tk.Label(f, text=label, bg="white",
                 anchor="w").pack(side="left", fill="x", expand=True)

        v = tk.DoubleVar(value=default)
        vars_dict[key] = v
        # Entry stylisée
        e = tk.Entry(f, textvariable=v, width=8, bg="#F5F5F5",
                     relief="flat", justify="center")
        e.pack(side="right")

    def create_action_row(self, parent, name, vars_dict, k_t, k_n,
                          k_p, k_pen, d_t, d_n, d_p, d_pen):
        f = tk.Frame(parent, bg="white")
        f.pack(fill="x", pady=2)

        # Label Nom
        tk.Label(f, text=name, bg="white", width=8, anchor="w",
                 font=("Segoe UI", 9, "bold")).pack(side="left")

        # Champs
        configs = [(k_t, d_t), (k_n, d_n), (k_p, d_p), (k_pen, d_pen)]
        for key, default in configs:
            v = tk.DoubleVar(value=default)
            vars_dict[key] = v
            e = tk.Entry(f, textvariable=v, width=8, bg="#F5F5F5",
                         relief="flat", justify="center")
            e.pack(side="left", padx=2)

    def run(self):
        self.fill_cfg(self.cfg_blue, self.vars_b)
        self.fill_cfg(self.cfg_yellow, self.vars_y)
        self.root.destroy()

        # Simulation call
        print("Lancement...")
        # import main
        # main.run_visualization(self.cfg_blue, self.cfg_yellow)

    def fill_cfg(self, cfg, vars):
        cfg.risk = vars['risk'].get()
        cfg.aggro = vars['aggro'].get()
        cfg.speed = vars['speed'].get()
        cfg.speed_noise = vars['speed_noise'].get()
        cfg.prob_move_fail = vars['p_move'].get()
        cfg.time_move_fail = vars['t_move_lost'].get()
        cfg.t_pick = vars['t_pick'].get()
        cfg.t_pick_noise = vars['noise_pick'].get()
        cfg.prob_pick_fail = vars['p_pick'].get()
        cfg.time_pick_fail = vars['pen_pick'].get()
        cfg.t_drop = vars['t_drop'].get()
        cfg.t_drop_noise = vars['noise_drop'].get()
        cfg.prob_drop_fail = vars['p_drop'].get()
        cfg.time_drop_fail = vars['pen_drop'].get()


if __name__ == "__main__":
    root = tk.Tk()
    app = Launcher(root)
    root.mainloop()
