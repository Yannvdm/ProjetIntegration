import tkinter as tk
from tkinter import ttk
from dataclasses import dataclass
import json
import sys

@dataclass
class RobotConfig:
    color: str
    capacity: int = 4
    risk: int = 50
    aggro: int = 0
    # Locomotion
    speed: float = 1000
    speed_noise: float = 50.0
    prob_move_fail: float = 0
    time_move_fail: float = 0
    # Prise objet
    t_pick: float = 1
    t_pick_noise: float = 0.5
    prob_pick_fail: float = 0
    time_pick_fail: float = 0
    # Dépose objet
    t_drop: float = 1
    t_drop_noise: float = 0.5
    prob_drop_fail: float = 0
    time_drop_fail: float = 0

class Launcher:
    def __init__(self, root):
        self.root = root
        self.root.title("Eurobot 2026 - Configuration")
        self.root.geometry("900x600") 

        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.root.bind('<Return>', lambda event: self.run())

        # On initialise un dictionnaire vide car on ne charge rien
        self.saved_data = {} 

        style = ttk.Style()
        style.theme_use('clam')
        style.configure("TLabel", background="white", font=("Segoe UI", 9))
        style.configure("TButton", font=("Segoe UI", 10, "bold"), padding=10)
        style.configure("Header.TLabel", font=("Segoe UI", 12, "bold"))
        style.configure("Card.TFrame", background="white", relief="flat")

        main_container = tk.Frame(root, bg="#f0f0f0")
        main_container.pack(fill="both", expand=True)

        self.cfg_blue = RobotConfig("bleu")
        self.cfg_yellow = RobotConfig("jaune")

        # --- CRÉATION DES COLONNES (Valeurs par défaut vides) ---
        self.vars_y = self.create_column(main_container, "ÉQUIPE JAUNE", "#FFFDE7", "#F9A825", 0, {})
        self.vars_b = self.create_column(main_container, "ÉQUIPE BLEUE", "#E3F2FD", "#1565C0", 1, {})
        
        btn_frame = tk.Frame(root, bg="#f0f0f0", pady=10)
        btn_frame.pack(side="bottom", fill="x")

        self.btn = tk.Button(btn_frame,
                        text="LANCER LA SIMULATION (Entrée)", 
                        command=self.run,
                        bg="#4CAF50", fg="white", 
                        font=("Segoe UI", 12, "bold"),
                        relief="flat", cursor="hand2", padx=20, pady=10)
        self.btn.pack()

    def on_closing(self):
        print("Fermeture sans lancer.")
        self.root.destroy()
        sys.exit()

    def create_column(self, parent, title, bg_color, title_color, col_index, saved_vals):
        col_frame = tk.Frame(parent, bg=bg_color)
        col_frame.pack(side="left", fill="both", expand=True, padx=(0 if col_index == 0 else 2))

        lbl_title = tk.Label(col_frame, text=title, bg=bg_color, fg=title_color, font=("Segoe UI", 16, "bold"), pady=10)
        lbl_title.pack(fill="x")

        vars = {}

        card_strat = self.create_card(col_frame, "STRATÉGIE")
        vars['risk'] = self.create_slider(card_strat, "Stratégie (Risque)", 50, "NID", "GARDE-MANGER")
        vars['aggro'] = self.create_slider(card_strat, "Agressivité", 0, "Passif", "Voleur")
        self.create_row_entry(card_strat, "Capacité Max", vars, 'capacity', 4)

        card_loco = self.create_card(col_frame, "LOCOMOTION")
        self.create_row_entry(card_loco, "Vitesse (mm/s)", vars, 'speed', 1000)
        self.create_row_entry(card_loco, "Bruit Vit. (+/-)", vars, 'speed_noise', 50) # Remis à 50 par défaut (400 c'est énorme)
        
        self.create_row_entry(card_loco, "Prob. Fail (%)", vars, 'p_move', 0)
        self.create_row_entry(card_loco, "Tps Fail (s)", vars, 't_move_lost', 0)

        card_act = self.create_card(col_frame, "ACTIONS")
        h_frame = tk.Frame(card_act, bg="white")
        h_frame.pack(fill="x")
        headers = ["Act.", "Tps(s)", "+Bruit", "Fail%", "+Pen"]
        for h in headers:
            tk.Label(h_frame, text=h, bg="white", fg="#666", font=("Segoe UI", 7, "bold"), width=8).pack(side="left")

        # Valeurs par défaut directement ici
        self.create_action_row(card_act, "Prise", vars, 't_pick', 'noise_pick', 'p_pick', 'pen_pick', 2.0, 0.5, 0.0, 0.0)
        self.create_action_row(card_act, "Pose", vars, 't_drop', 'noise_drop', 'p_drop', 'pen_drop', 2.0, 0.5, 0.0, 0.0)

        return vars

    def create_card(self, parent, title):
        card = ttk.Frame(parent, style="Card.TFrame", padding=10)
        card.pack(fill="x", padx=10, pady=5)
        lbl = ttk.Label(card, text=title, style="Header.TLabel", foreground="#333")
        lbl.pack(anchor="w", pady=(0, 5))
        return card

    def create_slider(self, parent, label, default_val, txt_left, txt_right):
        f = tk.Frame(parent, bg="white")
        f.pack(fill="x", pady=2)
        top = tk.Frame(f, bg="white")
        top.pack(fill="x")
        tk.Label(top, text=label, bg="white", font=("Segoe UI", 8, "bold")).pack(side="left")
        val_lbl = tk.Label(top, text=f"{int(default_val)}%", bg="#eee", width=4, font=("Consolas", 8))
        val_lbl.pack(side="right")
        var = tk.IntVar(value=int(default_val))
        def upd(v): val_lbl.config(text=f"{int(float(v))}%")
        scale = ttk.Scale(f, from_=0, to=100, variable=var, command=upd)
        scale.pack(fill="x")
        bot = tk.Frame(f, bg="white")
        bot.pack(fill="x")
        tk.Label(bot, text=txt_left, bg="white", fg="#888", font=("Segoe UI", 6)).pack(side="left")
        tk.Label(bot, text=txt_right, bg="white", fg="#888", font=("Segoe UI", 6)).pack(side="right")
        return var

    def create_row_entry(self, parent, label, vars_dict, key, default_val):
        f = tk.Frame(parent, bg="white")
        f.pack(fill="x", pady=1)
        tk.Label(f, text=label, bg="white", anchor="w", font=("Segoe UI", 8)).pack(side="left", fill="x", expand=True)
        v = tk.DoubleVar(value=default_val)
        vars_dict[key] = v
        tk.Entry(f, textvariable=v, width=6, bg="#F5F5F5", relief="flat", justify="center").pack(side="right")

    def create_action_row(self, parent, name, vars_dict, k_t, k_n, k_p, k_pen, d_t, d_n, d_p, d_pen):
        f = tk.Frame(parent, bg="white")
        f.pack(fill="x", pady=1)
        tk.Label(f, text=name, bg="white", width=8, anchor="w", font=("Segoe UI", 8, "bold")).pack(side="left")
        configs = [(k_t, d_t), (k_n, d_n), (k_p, d_p), (k_pen, d_pen)]
        for key, default in configs:
            v = tk.DoubleVar(value=default)
            vars_dict[key] = v
            tk.Entry(f, textvariable=v, width=6, bg="#F5F5F5", relief="flat", justify="center").pack(side="left", padx=1)

    def run(self):
        self.fill_cfg(self.cfg_blue, self.vars_b)
        self.fill_cfg(self.cfg_yellow, self.vars_y)
        self.root.destroy()
        print("Configuration validée ! Lancement...")

    def fill_cfg(self, cfg, vars):
        try:
            cfg.risk = vars['risk'].get()
            cfg.aggro = vars['aggro'].get()
            cfg.capacity = int(vars['capacity'].get())
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
        except ValueError:
            print("Attention : Valeur incorrecte, utilisation des défauts.")

if __name__ == "__main__":
    root = tk.Tk()
    app = Launcher(root)
    root.mainloop()