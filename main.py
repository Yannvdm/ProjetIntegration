from machine import Pin, PWM, time_pulse_us
import time
import network
from umqtt.simple import MQTTClient
import ujson
from buzzer import Buzzer

# --- Emergency Button Setup ---
bai = Pin(28, Pin.IN, Pin.PULL_UP)
buz = Buzzer()

# Check if the emergency button is pressed before starting
if bai.value() == 0:
    print("Emergency button is still pressed! Exiting…")
    buz.error_tone()
    sys.exit()  # Terminate the program immediately

buz.boot_tone()

# --- CONFIGURATION WIFI ---
SSID = "CharlesRed13"
PASS = "123456789"
MQTT_SERV = "192.168.137.101"
MQTT_TOPIC_STATUS = "robot/status"
CLIENT_ID = "pico_robot"

# --- REGLAGES MOTEURS & LOGIQUE ---
VITESSE_BASE = 14000      # Vitesse croisière
VITESSE_VIRAGE = 18000    # Vitesse forte pour le virage

# IMPORTANT : Temps du virage aveugle (pour faire ~20 degrés)
# 0.25 = 1/4 de seconde. Ajuste cette valeur !
DUREE_VIRAGE = 0.35

# --- PINS (Corrigés selon ton test) ---
enA = PWM(Pin(0));
in3 = Pin(2, Pin.OUT);
in4 = Pin(1, Pin.OUT)
enB = PWM(Pin(3));
in1 = Pin(4, Pin.OUT);
in2 = Pin(6, Pin.OUT)
enA.freq(1000);
enB.freq(1000)

# Capteurs Ultrasons (Réactivés)
TRIG = Pin(7, Pin.OUT);
ECHO = Pin(8, Pin.IN)

# Capteurs IR (Corrigés : 10 et 11)
IR_GAUCHE = Pin(10, Pin.IN);
IR_DROIT = Pin(11, Pin.IN)

LED = Pin(25, Pin.OUT)

# Variables globales
action_caisse_type = None
last_dir_A = 0; last_dir_B = 0
last_pwm_A = 0; last_pwm_B = 0
last_state = None  # Track the last state for sound signals

# --- CONNEXION ---
wlan = network.WLAN(network.STA_IF)
wlan.active(True)
wlan.connect(SSID, PASS)
print("Connexion WiFi...")
# Timeout pour ne pas bloquer si pas de wifi
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


# --- PILOTAGE ---

def stop_moteurs():
    global last_dir_A, last_dir_B, last_pwm_A, last_pwm_B
    enA.duty_u16(0); enB.duty_u16(0)
    in1.low(); in2.low(); in3.low(); in4.low()
    last_dir_A = 0; last_dir_B = 0
    last_pwm_A = 0; last_pwm_B = 0


def piloter(vg, vd):
    global last_dir_A, last_dir_B, last_pwm_A, last_pwm_B

    da = 1 if vg > 0 else (-1 if vg < 0 else 0)
    db = 1 if vd > 0 else (-1 if vd < 0 else 0)

    if (da != 0 and da != last_dir_A) or (db != 0 and db != last_dir_B):
        enA.duty_u16(0); enB.duty_u16(0)

    if vg > 0: in3.high(); in4.low()
    elif vg < 0: in3.low(); in4.high()
    else: in3.low(); in4.low()

    if vd > 0: in1.high(); in2.low()
    elif vd < 0: in1.low(); in2.high()
    else: in1.low(); in2.low()

    target_pwm_A = abs(int(vg))
    target_pwm_B = abs(int(vd))

    # Kickstart
    if (target_pwm_A > 0 and last_pwm_A == 0) or (target_pwm_B > 0 and last_pwm_B == 0):
        enA.duty_u16(40000); enB.duty_u16(40000)
        time.sleep(0.05)

    enA.duty_u16(target_pwm_A)
    enB.duty_u16(target_pwm_B)

    last_dir_A = da; last_dir_B = db
    last_pwm_A = target_pwm_A; last_pwm_B = target_pwm_B


# --- MAIN ---

print("Go: Robot Complet (Nouvelle Logique IR).")
stop_moteurs()
tick_log = 0

print(":) HELLO")
while True:
    try:
        client.check_msg()
    except:
        pass

    # Check if the emergency button is pressed
    if bai.value() == 0:
        current_state = "switch_stop"
        if last_state != current_state:
            print("Robot stopped by emergency button!")
            buz.emergency_stop_tone()
        stop_moteurs()
        break

    dist = get_distance()

    # 1. ACTION CAISSE (Priorité Vision)
    if action_caisse_type:
        stop_moteurs()
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
            for _ in range(6):
                LED.toggle()
                time.sleep(0.3)
        action_caisse_type = None
        stop_moteurs()
        time.sleep(0.5)
        continue

    # 2. OBSTACLE (Ultrasons)
    if dist < 20:
        current_state = "obstacle"
        if last_state != current_state:
            buz.obstacle_detected_tone()
        stop_moteurs()
        send_mqtt("Urgence", "Evitement", dist, True)
        print("Obstacle !")
        piloter(-VITESSE_BASE, -VITESSE_BASE)
        time.sleep(0.5)
        piloter(VITESSE_VIRAGE, -VITESSE_VIRAGE)
        time.sleep(0.6)
        stop_moteurs()
        last_state = current_state
        continue

    # 3. SUIVI LIGNE (NOUVELLE LOGIQUE BLIND TURN)
    g = IR_GAUCHE.value()
    d = IR_DROIT.value()
    manoeuvre = ""
    current_state = None

    # Cas 1: Ligne au centre (Tout va bien)
    if g == 0 and d == 0:
        current_state = "forward"
        if last_state != current_state:
            buz.move_forward_tone()
        piloter(VITESSE_BASE, VITESSE_BASE)
        manoeuvre = "Tout droit"
        time.sleep(0.01)
    # Cas 2: Touche à Gauche -> Virage FORCÉ
    elif g == 1 and d == 0:
        current_state = "turn_left"
        if last_state != current_state:
            buz.turn_detected_tone()
        manoeuvre = "Virage Force G"
        print("Détection G -> Virage Forcé")
        piloter(-VITESSE_VIRAGE, VITESSE_VIRAGE)
        time.sleep(DUREE_VIRAGE)
    # Cas 3: Touche à Droite -> Virage FORCÉ
    elif g == 0 and d == 1:
        current_state = "turn_right"
        if last_state != current_state:
            buz.turn_detected_tone()
        manoeuvre = "Virage Force D"
        print("Détection D -> Virage Forcé")
        piloter(VITESSE_VIRAGE, -VITESSE_VIRAGE)
        time.sleep(DUREE_VIRAGE)
    # Cas 4: Intersection ou Stop
    elif g == 1 and d == 1:
        current_state = "stop"
        if last_state != current_state:
            buz.stop_tone()
        manoeuvre = "Stop Ligne"
        stop_moteurs()
        time.sleep(0.1)
    else:
        current_state = "lost"
        piloter(VITESSE_BASE, VITESSE_BASE)
        manoeuvre = "Perdu/Cherche"
        time.sleep(0.01)

    last_state = current_state  # Update the last state

    # Logs MQTT (pour debug)
    tick_log += 1
    if tick_log > 10:
        send_mqtt("Suivi", manoeuvre, dist, False)
        tick_log = 0

print(":( GOODBYE")
