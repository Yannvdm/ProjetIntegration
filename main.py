from machine import Pin, PWM, time_pulse_us
import time
import network
from umqtt.simple import MQTTClient
import ujson

# --- CONFIGURATION WIFI ---
SSID = "CharlesRed13"
PASS = "123456789"
MQTT_SERV = "192.168.137.101"
MQTT_TOPIC_STATUS = "robot/status"
CLIENT_ID = "pico_robot"

# --- REGLAGES MOTEURS & SUIVI AVANCÉ ---
# Vitesses adaptées à ton robot (basse vitesse + kickstart)
VITESSE_BASE = 14000  # Vitesse croisière
VITESSE_CORR = 8000  # Vitesse roue intérieure (virage doux)
VITESSE_VIRAGE = 18000  # Vitesse pour rotation sur place (virage fort)

# Paramètres du suivi intelligent
NB_CYCLES_VIRAGE = 3  # Sensibilité: après 3 cycles sur la ligne, on tourne fort
compteur_gauche = 0
compteur_droite = 0

# --- PINS ---
enA = PWM(Pin(0));
in3 = Pin(2, Pin.OUT);
in4 = Pin(1, Pin.OUT)
enB = PWM(Pin(3));
in1 = Pin(4, Pin.OUT);
in2 = Pin(6, Pin.OUT)
enA.freq(1000);
enB.freq(1000)

# Capteurs
TRIG = Pin(7, Pin.OUT);
ECHO = Pin(8, Pin.IN)
IR_GAUCHE = Pin(10, Pin.IN);
IR_DROIT = Pin(11, Pin.IN)
LED = Pin(25, Pin.OUT)

# Variables globales état
action_caisse_type = None
last_dir_A = 0;
last_dir_B = 0
last_pwm_A = 0;
last_pwm_B = 0

# --- CONNEXION ---
wlan = network.WLAN(network.STA_IF)
wlan.active(True)
wlan.connect(SSID, PASS)
print("Connexion WiFi...")
# Petit timeout pour éviter de bloquer si pas de wifi
timeout = 0
while not wlan.isconnected() and timeout < 20:
    LED.toggle();
    time.sleep(0.2)
    timeout += 1

if wlan.isconnected():
    LED.value(1)
    print("Connecté IP:", wlan.ifconfig()[0])
else:
    print("Mode Hors Ligne (Pas de WiFi)")

client = MQTTClient(CLIENT_ID, MQTT_SERV)


def callback(topic, msg):
    global action_caisse_type
    print("MQTT:", msg)
    if msg == b'CAISSE_NOIRE':  action_caisse_type = "NOIRE"
    if msg == b'CAISSE_COULEUR': action_caisse_type = "COULEUR"


try:
    if wlan.isconnected():
        client.connect()
        client.set_callback(callback)
        client.subscribe(b"robot/vision_event")
        print("MQTT OK")
except Exception as e:
    print("Err MQTT", e)


# --- FONCTIONS ---

def send_mqtt(etat, manoeuvre, dist=0, obs=False):
    # On n'envoie que si connecté
    if not wlan.isconnected(): return
    msg = ujson.dumps({"etat": etat, "manoeuvre": manoeuvre, "distance": round(dist, 1), "obstacle": obs})
    try:
        client.publish(MQTT_TOPIC_STATUS, msg)
    except:
        pass


def get_distance():
    TRIG.value(0);
    time.sleep_us(2)
    TRIG.value(1);
    time.sleep_us(10);
    TRIG.value(0)
    try:
        d = time_pulse_us(ECHO, 1, 30000)
        return (d * 0.0343) / 2 if d > 0 else 999
    except:
        return 999


# --- PILOTAGE AVEC KICKSTART (Le coeur du Code 1) ---

def stop_moteurs():
    global last_dir_A, last_dir_B, last_pwm_A, last_pwm_B
    enA.duty_u16(0);
    enB.duty_u16(0)
    in1.low();
    in2.low();
    in3.low();
    in4.low()
    last_dir_A = 0;
    last_dir_B = 0
    last_pwm_A = 0;
    last_pwm_B = 0
    # Pas de sleep ici pour garder la réactivité du suivi de ligne avancé


def piloter(vg, vd):
    """
    vg: Vitesse Gauche (-65535 à +65535)
    vd: Vitesse Droite (-65535 à +65535)
    Gère le H-Bridge et le Kickstart
    """
    global last_dir_A, last_dir_B, last_pwm_A, last_pwm_B

    # Directions
    da = 1 if vg > 0 else (-1 if vg < 0 else 0)
    db = 1 if vd > 0 else (-1 if vd < 0 else 0)

    # Protection changement brusque direction
    if (da != 0 and da != last_dir_A) or (db != 0 and db != last_dir_B):
        enA.duty_u16(0);
        enB.duty_u16(0)  # Micro pause électrique

    # Configuration des pins de direction
    # Moteur A (Gauche)
    if vg > 0:
        in3.high(); in4.low()
    elif vg < 0:
        in3.low(); in4.high()
    else:
        in3.low(); in4.low()

    # Moteur B (Droit)
    if vd > 0:
        in1.high(); in2.low()
    elif vd < 0:
        in1.low(); in2.high()
    else:
        in1.low(); in2.low()

    target_pwm_A = abs(int(vg))
    target_pwm_B = abs(int(vd))

    # --- LE KICKSTART ---
    # Si on demande de la vitesse alors qu'on était à l'arrêt
    if (target_pwm_A > 0 and last_pwm_A == 0) or (target_pwm_B > 0 and last_pwm_B == 0):
        # Boost de démarrage (40000 pendant 50ms)
        enA.duty_u16(40000)
        enB.duty_u16(40000)
        time.sleep(0.05)

        # Application vitesse demandée
    enA.duty_u16(target_pwm_A)
    enB.duty_u16(target_pwm_B)

    last_dir_A = da;
    last_dir_B = db
    last_pwm_A = target_pwm_A;
    last_pwm_B = target_pwm_B


# --- MAIN ---

print("Go: Robot Hybride (MQTT + Suivi Avancé).")
stop_moteurs()
tick_log = 0

while True:
    # Gestion MQTT non-bloquante
    try:
        client.check_msg()
    except:
        pass

    dist = get_distance()

    # 1. ACTION CAISSE (Priorité Vision)
    if action_caisse_type:
        stop_moteurs()
        # Reset des compteurs de ligne pour éviter comportement étrange après reprise
        compteur_gauche = 0;
        compteur_droite = 0

        if action_caisse_type == "NOIRE":
            print("Action: Noire")
            send_mqtt("Action", "Avance/Recul", dist, False)
            piloter(VITESSE_BASE, VITESSE_BASE)
            time.sleep(1.0)
            stop_moteurs()
            time.sleep(0.5)
            piloter(-VITESSE_BASE, -VITESSE_BASE)
            time.sleep(1.0)
        elif action_caisse_type == "COULEUR":
            print("Action: Couleur")
            send_mqtt("Action", "Bras Simulé", dist, False)
            for _ in range(6): LED.toggle(); time.sleep(0.3)

        action_caisse_type = None
        stop_moteurs()
        time.sleep(0.5)
        continue

    # 2. OBSTACLE (Sécurité)
    if dist < 20:
        stop_moteurs()
        send_mqtt("Urgence", "Evitement", dist, True)
        print("Obstacle détecté")
        # Manoeuvre d'évitement
        piloter(-VITESSE_BASE, -VITESSE_BASE)  # Recule
        time.sleep(0.5)
        piloter(VITESSE_VIRAGE, -VITESSE_VIRAGE)  # Tourne sur place
        time.sleep(0.6)
        stop_moteurs()
        compteur_gauche = 0;
        compteur_droite = 0  # Reset logique ligne
        continue

    # 3. SUIVI LIGNE AVANCÉ (Intégration du Code 2)
    # Lecture capteurs (0=Blanc, 1=Noir)
    g = IR_GAUCHE.value()
    d = IR_DROIT.value()

    manoeuvre = ""

    # Cas 1: Ligne au centre (Tout va bien)
    if g == 0 and d == 0:
        piloter(VITESSE_BASE, VITESSE_BASE)
        compteur_gauche = 0
        compteur_droite = 0
        manoeuvre = "Tout droit"

    # Cas 2: Dévie à droite (Capteur Gauche touche la ligne)
    elif g == 1 and d == 0:
        compteur_gauche += 1
        compteur_droite = 0

        if compteur_gauche >= NB_CYCLES_VIRAGE:
            # Virage fort à Gauche (Pivot sur place)
            piloter(-VITESSE_VIRAGE, VITESSE_VIRAGE)
            manoeuvre = "Virage Fort G"
        else:
            # Correction Douce à Gauche (Roue Gauche ralentie)
            piloter(VITESSE_CORR, VITESSE_BASE)
            manoeuvre = "Correction G"

    # Cas 3: Dévie à gauche (Capteur Droit touche la ligne)
    elif g == 0 and d == 1:
        compteur_droite += 1
        compteur_gauche = 0

        if compteur_droite >= NB_CYCLES_VIRAGE:
            # Virage fort à Droite (Pivot sur place)
            piloter(VITESSE_VIRAGE, -VITESSE_VIRAGE)
            manoeuvre = "Virage Fort D"
        else:
            # Correction Douce à Droite (Roue Droite ralentie)
            piloter(VITESSE_BASE, VITESSE_CORR)
            manoeuvre = "Correction D"

    # Cas 4: Intersection ou Arrêt
    elif g == 1 and d == 1:
        stop_moteurs()
        compteur_gauche = 0
        compteur_droite = 0
        manoeuvre = "Stop Ligne"

    else:
        # Cas perdu (optionnel, on s'arrête)
        stop_moteurs()
        manoeuvre = "Perdu"

    # Log MQTT moins fréquent pour ne pas saturer
    tick_log += 1
    if tick_log > 20:  # Toutes les ~1 seconde
        send_mqtt("Suivi", manoeuvre, dist, False)
        tick_log = 0

    # Petite pause pour la fréquence de boucle
    # Attention: Trop lent = on rate la ligne, Trop vite = instable
    time.sleep(0.05)