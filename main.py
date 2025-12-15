from machine import Pin, PWM, time_pulse_us
import time
import network
from umqtt.simple import MQTTClient
import ujson
from buzzer import Buzzer

# --- CONFIGURATION WIFI ---
SSID = "CharlesRed13"
PASS = "123456789"
MQTT_SERV = "192.168.137.101"
MQTT_TOPIC_STATUS = "robot/status"
CLIENT_ID = "pico_robot"

# --- REGLAGES MOTEURS ---
VITESSE_BASE = 15000  # On garde une base saine
VITESSE_VIRAGE = 26000  # BOOSTÉ (était 20000) pour tourner sec

# TEMPS DU VIRAGE
DUREE_VIRAGE = 0.35

# --- PINS ---
bai = Pin(28, Pin.IN, Pin.PULL_UP)
buz = Buzzer()

enA = PWM(Pin(0));
in3 = Pin(2, Pin.OUT);
in4 = Pin(1, Pin.OUT)
enB = PWM(Pin(3));
in1 = Pin(4, Pin.OUT);
in2 = Pin(6, Pin.OUT)
enA.freq(1000);
enB.freq(1000)

TRIG = Pin(7, Pin.OUT);
ECHO = Pin(8, Pin.IN)
IR_GAUCHE = Pin(10, Pin.IN);
IR_DROIT = Pin(11, Pin.IN)

# Gestion LED Pico W
try:
    LED = Pin("LED", Pin.OUT)
except:
    LED = Pin(25, Pin.OUT)

# Variables globales
action_caisse_type = None
last_dir_A = 0;
last_dir_B = 0
last_pwm_A = 0;
last_pwm_B = 0

# --- VERIFICATION BOUTON ARRET ---
if bai.value() == 0:
    print("URGENCE: Bouton appuyé au démarrage.")
    buz.error_tone()
    while bai.value() == 0:
        time.sleep(0.1)
    print("Bouton relâché, démarrage...")

buz.boot_tone()

# --- CONNEXION WIFI ---
wlan = network.WLAN(network.STA_IF)
wlan.active(True)
wlan.connect(SSID, PASS)
print("Connexion WiFi en cours...")

# Optimisation: Timeout plus court (5 sec max pour le wifi)
timeout = 0
while not wlan.isconnected() and timeout < 25:
    LED.toggle()
    time.sleep(0.2)
    timeout += 1

if wlan.isconnected():
    LED.value(1)
    print("WiFi OK:", wlan.ifconfig()[0])
else:
    print("ECHEC WiFi (Mode Hors Ligne)")
    for _ in range(4): LED.toggle(); time.sleep(0.1)

# --- CONNEXION MQTT ---
client = MQTTClient(CLIENT_ID, MQTT_SERV)


def callback(topic, msg):
    global action_caisse_type
    print("Reçu:", msg)
    if msg == b'CAISSE_NOIRE':  action_caisse_type = "NOIRE"
    if msg == b'CAISSE_COULEUR': action_caisse_type = "COULEUR"
    if msg == b'ACTION_NID': action_caisse_type = "NID"


try:
    if wlan.isconnected():
        print(f"Connexion MQTT à {MQTT_SERV}...")  # Si ça bloque ici 20s, c'est le pare-feu du PC
        client.connect()
        client.set_callback(callback)
        client.subscribe(b"robot/vision_event")
        print("MQTT Connecté !")
except Exception as e:
    print("Erreur MQTT (Pas grave, on continue):", e)


# --- FONCTIONS ---

def send_mqtt(etat, manoeuvre, dist=0, obs=False):
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
    time.sleep_us(10)
    TRIG.value(0)
    try:
        d = time_pulse_us(ECHO, 1, 10000)  # Timeout court (10ms)
        return (d * 0.0343) / 2 if d > 0 else 999
    except:
        return 999


def stop_moteurs():
    global last_dir_A, last_dir_B, last_pwm_A, last_pwm_B
    enA.duty_u16(0);
    enB.duty_u16(0)
    in1.low();
    in2.low();
    in3.low();
    in4.low()
    last_dir_A = 0;
    last_dir_B = 0;
    last_pwm_A = 0;
    last_pwm_B = 0


def piloter(vg, vd):
    global last_dir_A, last_dir_B, last_pwm_A, last_pwm_B
    da = 1 if vg > 0 else (-1 if vg < 0 else 0)
    db = 1 if vd > 0 else (-1 if vd < 0 else 0)

    if (da != 0 and da != last_dir_A) or (db != 0 and db != last_dir_B):
        enA.duty_u16(0);
        enB.duty_u16(0)

    if vg > 0:
        in3.high(); in4.low()
    elif vg < 0:
        in3.low(); in4.high()
    else:
        in3.low(); in4.low()

    if vd > 0:
        in1.high(); in2.low()
    elif vd < 0:
        in1.low(); in2.high()
    else:
        in1.low(); in2.low()

    t_A = abs(int(vg));
    t_B = abs(int(vd))

    # Kickstart
    if (t_A > 0 and last_pwm_A == 0) or (t_B > 0 and last_pwm_B == 0):
        enA.duty_u16(45000);
        enB.duty_u16(45000);
        time.sleep(0.02)

    enA.duty_u16(t_A);
    enB.duty_u16(t_B)
    last_dir_A = da;
    last_dir_B = db;
    last_pwm_A = t_A;
    last_pwm_B = t_B


# --- BOUCLE PRINCIPALE ---

print("PRET AU DEPART !")
stop_moteurs()
tick_log = 0

while True:
    try:
        client.check_msg()
    except:
        pass

    if bai.value() == 0:
        buz.emergency_stop_tone()
        stop_moteurs()
        break

    dist = get_distance()

    # --- 1. ACTION CAISSE ---
    if action_caisse_type:
        buz.box_detect()
        stop_moteurs()

        if action_caisse_type == "NOIRE":
            print("Action: Noire")
            send_mqtt("Action", "Caisse Noire", dist, False)
            piloter(-VITESSE_BASE, -VITESSE_BASE)
            time.sleep(1.0)
            stop_moteurs()
            time.sleep(0.2)
            piloter(VITESSE_BASE, VITESSE_BASE)
            time.sleep(1.0)

        elif action_caisse_type == "COULEUR":
            print("Action: Couleur")
            send_mqtt("Action", "Caisse Couleur", dist, False)
            stop_moteurs()
            # 3 Secondes de clignotement
            for _ in range(10):
                LED.toggle()
                time.sleep(0.3)
            if wlan.isconnected(): LED.value(1)

        elif action_caisse_type == "NID":
            print("Action: Nid trouvé !")
            send_mqtt("Action", "Nid (Pause 10s)", dist, False)
            stop_moteurs()

            # Boucle de 10 secondes (20 tours de 0.5s)
            for _ in range(20):
                buz.nid_tone()  # Bip sonore défini dans buzzer.py
                LED.toggle()  # Clignotement visuel
                time.sleep(0.5)  # Pause entre les bips

            if wlan.isconnected(): LED.value(1)

        action_caisse_type = None
        stop_moteurs()
        time.sleep(0.5)
        continue

    # --- 2. OBSTACLE ---
    if dist < 20:
        buz.obstacle_detected_tone()
        stop_moteurs()
        send_mqtt("Urgence", "Evitement", dist, True)
        piloter(-VITESSE_BASE, -VITESSE_BASE)
        time.sleep(0.5)
        piloter(VITESSE_VIRAGE, -VITESSE_VIRAGE)
        time.sleep(0.5)
        stop_moteurs()
        continue

    # --- 3. SUIVI LIGNE (AVEC SONS) ---
    g = IR_GAUCHE.value()
    d = IR_DROIT.value()
    manoeuvre = ""

    if g == 0 and d == 0:
        piloter(VITESSE_BASE, VITESSE_BASE)
        manoeuvre = "Tout droit"

    elif g == 1 and d == 0:
        manoeuvre = "Virage G"
        piloter(-VITESSE_VIRAGE, VITESSE_VIRAGE)

        # ASTUCE SONORE : On active le buzzer MANUELLEMENT pendant qu'il tourne
        # Cela ne bloque pas le robot, car on utilise le sleep du virage pour le son
        buz.buzzer.freq(1200)  # Fréquence virage
        buz.buzzer.duty_u16(30000)  # Volume ON
        time.sleep(DUREE_VIRAGE)  # Le robot tourne ET sonne pendant 0.25s
        buz.buzzer.duty_u16(0)  # Volume OFF

    elif g == 0 and d == 1:
        manoeuvre = "Virage D"
        piloter(VITESSE_VIRAGE, -VITESSE_VIRAGE)

        # ASTUCE SONORE (Idem)
        buz.buzzer.freq(1200)
        buz.buzzer.duty_u16(30000)
        time.sleep(DUREE_VIRAGE)
        buz.buzzer.duty_u16(0)

    elif g == 1 and d == 1:
        manoeuvre = "Stop Ligne"
        stop_moteurs()
        # Petit bip court pour l'intersection
        buz.buzzer.freq(500);
        buz.buzzer.duty_u16(30000)
        time.sleep(0.1)
        buz.buzzer.duty_u16(0)

    else:
        piloter(VITESSE_BASE, VITESSE_BASE)
        manoeuvre = "Cherche"

    tick_log += 1
    if tick_log > 5:
        send_mqtt("Suivi", manoeuvre, dist, False)
        tick_log = 0