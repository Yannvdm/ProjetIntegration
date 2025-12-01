from machine import Pin, PWM, time_pulse_us
import time
import network
from umqtt.simple import MQTTClient
import ujson

# --- CONFIGURATION WIFI ---
SSID = "CharlesRed13"
PASS = "123456789"
MQTT_SERV = "192.168.137.101"  # Ton IP actuelle
MQTT_TOPIC_STATUS = "robot/status"
CLIENT_ID = "pico_robot"

# --- REGLAGES MOTEURS (VITESSE ESCARGOT) ---
# On descend très bas. Si le robot "siffle" mais ne bouge pas après le démarrage,
# augmente ces valeurs par pas de 1000 (ex: 14000, 15000).
VITESSE_BASE = 13000  # ~20% de puissance
VITESSE_TOURNE = 16000  # Un peu plus pour tourner

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
IR_GAUCHE = Pin(16, Pin.IN);
IR_DROIT = Pin(17, Pin.IN)
LED = Pin(25, Pin.OUT)

# Variables globales
action_caisse_type = None
last_dir_A = 0;
last_dir_B = 0
last_pwm_A = 0;
last_pwm_B = 0  # Pour savoir si on était à l'arrêt

# --- CONNEXION ---
wlan = network.WLAN(network.STA_IF)
wlan.active(True)
wlan.connect(SSID, PASS)
print("Connexion WiFi...")
while not wlan.isconnected():
    LED.toggle();
    time.sleep(0.2)
LED.value(1)
print("Connecté IP:", wlan.ifconfig()[0])

client = MQTTClient(CLIENT_ID, MQTT_SERV)


def callback(topic, msg):
    global action_caisse_type
    print("MQTT:", msg)
    if msg == b'CAISSE_NOIRE':  action_caisse_type = "NOIRE"
    if msg == b'CAISSE_COULEUR': action_caisse_type = "COULEUR"


try:
    client.connect()
    client.set_callback(callback)
    client.subscribe(b"robot/vision_event")
    print("MQTT OK")
except Exception as e:
    print("Err MQTT", e)


# --- FONCTIONS ---

def send_mqtt(etat, manoeuvre, dist=0, obs=False):
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


def lire_ligne():
    g = IR_GAUCHE.value();
    d = IR_DROIT.value()
    # 1=Noir, 0=Blanc
    if g == 1 and d == 1: return "CENTRE"
    if g == 1 and d == 0: return "GAUCHE"
    if g == 0 and d == 1: return "DROITE"
    return "PERDU"


# --- PILOTAGE AVEC KICKSTART ---

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
    time.sleep(0.05)


def piloter(vg, vd):
    global last_dir_A, last_dir_B, last_pwm_A, last_pwm_B

    # Directions
    da = 1 if vg > 0 else (-1 if vg < 0 else 0)
    db = 1 if vd > 0 else (-1 if vd < 0 else 0)

    # Protection inversion
    if (da != 0 and da != last_dir_A) or (db != 0 and db != last_dir_B):
        enA.duty_u16(0);
        enB.duty_u16(0);
        time.sleep(0.05)

    # Configuration des pins de direction
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

    target_pwm_A = abs(int(vg))
    target_pwm_B = abs(int(vd))

    # --- LE KICKSTART ---
    # Si on demande de la vitesse alors qu'on était à l'arrêt (ou presque)
    # On donne un coup de boost bref pour lancer le moteur
    if (target_pwm_A > 0 and last_pwm_A == 0) or (target_pwm_B > 0 and last_pwm_B == 0):
        # On applique 60% de puissance pendant un instant très court
        enA.duty_u16(40000)
        enB.duty_u16(40000)
        time.sleep(0.05)  # 50 millisecondes de boost

    # Ensuite on applique la vitesse (lente) demandée
    enA.duty_u16(target_pwm_A)
    enB.duty_u16(target_pwm_B)

    last_dir_A = da;
    last_dir_B = db
    last_pwm_A = target_pwm_A;
    last_pwm_B = target_pwm_B


# --- MAIN ---

print("Go.")
stop_moteurs()
tick_log = 0

while True:
    try:
        client.check_msg()
    except:
        pass

    dist = get_distance()

    # 1. ACTION CAISSE
    if action_caisse_type:
        stop_moteurs()
        if action_caisse_type == "NOIRE":
            print("Action: Noire")
            send_mqtt("Action", "Avance 1s", dist, False)
            piloter(VITESSE_BASE, VITESSE_BASE)
            time.sleep(1.0)
            stop_moteurs()
            send_mqtt("Action", "Recul 1s", dist, False)
            piloter(-VITESSE_BASE, -VITESSE_BASE)
            time.sleep(1.0)
        elif action_caisse_type == "COULEUR":
            print("Action: Couleur")
            send_mqtt("Action", "Bras 3s", dist, False)
            for _ in range(6): LED.toggle(); time.sleep(0.5)

        action_caisse_type = None
        stop_moteurs()
        send_mqtt("Auto", "Reprise", dist, False)
        continue

    # 2. OBSTACLE
    if dist < 20:
        stop_moteurs()
        send_mqtt("Urgence", "Obstacle", dist, True)
        piloter(-VITESSE_BASE, -VITESSE_BASE)
        time.sleep(0.5)
        piloter(VITESSE_TOURNE, -VITESSE_TOURNE)
        time.sleep(0.8)
        stop_moteurs()
        continue

    # 3. SUIVI LIGNE
    etat_ligne = lire_ligne()

    if etat_ligne == "CENTRE":
        piloter(VITESSE_BASE, VITESSE_BASE)
        manoeuvre = "Tout droit"
    elif etat_ligne == "GAUCHE":
        # Pivote doucement
        piloter(0, VITESSE_TOURNE)
        manoeuvre = "Gauche"
    elif etat_ligne == "DROITE":
        piloter(VITESSE_TOURNE, 0)
        manoeuvre = "Droite"
    else:
        # Recherche
        piloter(VITESSE_BASE, VITESSE_BASE)
        manoeuvre = "Cherche"

    tick_log += 1
    if tick_log > 10:
        send_mqtt("Suivi Ligne", manoeuvre, dist, False)
        tick_log = 0

    time.sleep(0.05)