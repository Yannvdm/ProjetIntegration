from machine import Pin, PWM, time_pulse_us
import time
import network
from umqtt.simple import MQTTClient
import ujson
from buzzer import Buzzer

# --- CONFIGURATION WIFI ---
SSID = "CharlesRed13"
PASS = "123456789"
MQTT_SERV = "192.168.137.49"  # Vérifie bien l'IP
MQTT_TOPIC_STATUS = "robot/status"
CLIENT_ID = "pico_robot"

# --- REGLAGES MOTEURS ---
VITESSE_BASE = 18000
VITESSE_VIRAGE = 28000
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


# =========================================================
# SEQUENCE DE DEMARRAGE (LOGIQUE MODIFIÉE)
# =========================================================

stop_moteurs()
buz.boot_tone()  # Petit son pour dire "Je suis sous tension"

# 1. D'ABORD LE WIFI (Indépendant du Raspberry)
# ---------------------------------------------
wlan = network.WLAN(network.STA_IF)
wlan.active(True)
wlan.connect(SSID, PASS)
print("Connexion WiFi en cours...")

timeout = 0
while not wlan.isconnected() and timeout < 25:
    LED.toggle()
    time.sleep(0.2)
    timeout += 1

if wlan.isconnected():
    print("WiFi OK:", wlan.ifconfig()[0])
    # 2 Bips rapides pour dire "WiFi OK"
    buz.buzzer.freq(2000);
    buz.buzzer.duty_u16(10000);
    time.sleep(0.1)
    buz.buzzer.duty_u16(0);
    time.sleep(0.1)
    buz.buzzer.duty_u16(10000);
    time.sleep(0.1);
    buz.buzzer.duty_u16(0)
else:
    print("ECHEC WiFi")
    buz.error_tone()
    while True:  # On bloque si pas de wifi
        LED.toggle();
        time.sleep(0.1)

# 2. ENSUITE LE BOUTON "STANDBY" (Temps de setup Raspberry)
# ---------------------------------------------------------
if bai.value() == 0:
    print("MODE SETUP: En attente libération bouton...")
    # Tant que le bouton est appuyé, on attend (LED clignote lentement)
    while bai.value() == 0:
        LED.toggle()
        time.sleep(1.0)  # Clignotement lent = "Je suis prêt, j'attends"

    print("Bouton relâché ! Lancement de la recherche Raspberry...")
    # Petit délai pour laisser le doigt partir
    time.sleep(1.0)

# 3. ENFIN LA CONNEXION MQTT (Maintenant que le Rasp est prêt)
# ------------------------------------------------------------
client = MQTTClient(CLIENT_ID, MQTT_SERV)


def callback(topic, msg):
    global action_caisse_type
    print(f"DEBUG RECEPTION: {msg}")
    message_propre = msg.strip()
    if message_propre == b'CAISSE_NOIRE':
        action_caisse_type = "NOIRE"
    elif message_propre == b'CAISSE_COULEUR':
        action_caisse_type = "COULEUR"
    elif message_propre == b'ACTION_NID':
        action_caisse_type = "NID"


print(f"Tentative connexion MQTT {MQTT_SERV}...")
mqtt_connected = False

# Boucle de connexion bloquante
while not mqtt_connected:
    try:
        client.connect()
        mqtt_connected = True
        print("MQTT Connecté ! GO !")
        LED.value(1)  # LED Fixe = Connecté
        buz.boot_tone()  # Musique de départ
    except Exception as e:
        print(f"Echec MQTT ({e}). Nouvel essai dans 2s...")
        # Bip d'attente
        LED.value(0)
        buz.buzzer.freq(500);
        buz.buzzer.duty_u16(10000);
        time.sleep(0.1);
        buz.buzzer.duty_u16(0)
        time.sleep(2.0)

client.set_callback(callback)
client.subscribe(b"robot/vision_event")


# =========================================================
# BOUCLE PRINCIPALE
# =========================================================

# --- FONCTIONS UTILITAIRES ---
def send_mqtt(etat, manoeuvre, dist=0, obs=False):
    msg = ujson.dumps({"etat": etat, "manoeuvre": manoeuvre, "distance": round(dist, 1), "obstacle": obs})
    try:
        client.publish(MQTT_TOPIC_STATUS, msg)
    except:
        pass


def get_distance():
    TRIG.value(0);
    time.sleep_us(2);
    TRIG.value(1);
    time.sleep_us(10);
    TRIG.value(0)
    try:
        d = time_pulse_us(ECHO, 1, 10000)
        return (d * 0.0343) / 2 if d > 0 else 999
    except:
        return 999


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


print("ROBOT EN ROUTE !")
tick_log = 0

while True:
    try:
        client.check_msg()
    except:
        pass

    if bai.value() == 0:
        buz.emergency_stop_tone()
        stop_moteurs()
        # Si on rapuie sur le bouton, on casse la boucle (fin du programme)
        # Ou on pourrait faire une boucle d'attente ici aussi pour redémarrer
        print("ARRET DEMANDE")
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
            for _ in range(10):
                LED.toggle()
                time.sleep(0.3)
                try:
                    client.check_msg()
                except:
                    pass
            LED.value(1)

        elif action_caisse_type == "NID":
            print("Action: Nid trouvé !")
            send_mqtt("Action", "Nid (Pause 10s)", dist, False)
            stop_moteurs()
            # Boucle d'attente
            for _ in range(20):
                buz.nid_tone()
                LED.toggle()
                try:
                    client.check_msg()
                except:
                    pass
                time.sleep(0.5)
            LED.value(1)

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

    # --- 3. SUIVI LIGNE ---
    g = IR_GAUCHE.value()
    d = IR_DROIT.value()
    manoeuvre = ""

    if g == 0 and d == 0:
        piloter(VITESSE_BASE, VITESSE_BASE)
        manoeuvre = "Tout droit"
    elif g == 1 and d == 0:
        manoeuvre = "Virage G"
        piloter(-VITESSE_VIRAGE, VITESSE_VIRAGE)
        buz.buzzer.freq(1200);
        buz.buzzer.duty_u16(30000)
        time.sleep(DUREE_VIRAGE)
        buz.buzzer.duty_u16(0)
    elif g == 0 and d == 1:
        manoeuvre = "Virage D"
        piloter(VITESSE_VIRAGE, -VITESSE_VIRAGE)
        buz.buzzer.freq(1200);
        buz.buzzer.duty_u16(30000)
        time.sleep(DUREE_VIRAGE)
        buz.buzzer.duty_u16(0)
    elif g == 1 and d == 1:
        manoeuvre = "Stop Ligne"
        stop_moteurs()
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