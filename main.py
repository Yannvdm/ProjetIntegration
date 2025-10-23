from machine import Pin, PWM, time_pulse_us
import time
import network
from umqtt.simple import MQTTClient
import ujson

# ---------- CONFIG WIFI ----------
SSID = "CharlesRed13"
PASS = "123456789"
wlan = network.WLAN(network.STA_IF)
wlan.active(True)
wlan.connect(SSID, PASS)
while not wlan.isconnected():
    time.sleep(1)
print("Connecté, IP:", wlan.ifconfig()[0])

# ---------- CONFIG MQTT ----------
MQTT_SERV = "10.171.184.167"
MQTT_TOPIC = "robot/status"
CLIENT_ID = "pico_robot"
client = MQTTClient(CLIENT_ID, MQTT_SERV)
client.connect()

# ---------- FLAGS ----------
running = True
stop_requested = False
obstacle = False

def sub_cb(topic, msg):
    global running, stop_requested
    print("Commande reçue:", topic, msg)
    if msg == b'stop':
        running = False
        stop_requested = True
    elif msg == b'start':
        running = True

client.set_callback(sub_cb)
client.subscribe(b"robot/command")

def send_mqtt(etat, manoeuvre, distance, obstacle):
    msg = ujson.dumps({
        "etat": etat,
        "manoeuvre": manoeuvre,
        "distance": round(distance,1),
        "obstacle": obstacle
    })
    try:
        client.publish(MQTT_TOPIC, msg)
    except Exception as e:
        print("Erreur MQTT:", e)

# ---------- MOTEURS ----------
enA = PWM(Pin(0)); in3 = Pin(2, Pin.OUT); in4 = Pin(1, Pin.OUT)
enB = PWM(Pin(3)); in1 = Pin(4, Pin.OUT); in2 = Pin(6, Pin.OUT)
enA.freq(1000); enB.freq(1000); VITESSE = 35000

def stop(distance):
    send_mqtt("Stop", "Arrêt", distance, obstacle)
    enA.duty_u16(0); enB.duty_u16(0)
    in1.low(); in2.low(); in3.low(); in4.low()

def avancer(distance, vitesse=VITESSE):
    global obstacle
    in3.high(); in4.low(); in1.high(); in2.low()
    enA.duty_u16(vitesse); enB.duty_u16(vitesse)
    send_mqtt("Avance", "Avancer", distance, obstacle)

def reculer(distance, vitesse=VITESSE):
    global obstacle
    in3.low(); in4.high(); in1.low(); in2.high()
    enA.duty_u16(vitesse); enB.duty_u16(vitesse)
    send_mqtt("Recul", "Reculer", distance, obstacle)

def tourner_gauche(distance, vitesse=VITESSE):
    global obstacle
    in3.low(); in4.high(); in1.high(); in2.low()
    enA.duty_u16(vitesse); enB.duty_u16(vitesse)
    send_mqtt("Tourne", "Gauche", distance, obstacle)

def tourner_droite(distance, vitesse=VITESSE):
    global obstacle
    in3.high(); in4.low(); in1.low(); in2.high()
    enA.duty_u16(vitesse); enB.duty_u16(vitesse)
    send_mqtt("Tourne", "Droite", distance, obstacle)

# ---------- CAPTEUR ULTRASON ----------
TRIG = Pin(7, Pin.OUT)
ECHO = Pin(8, Pin.IN)
LED = Pin(25, Pin.OUT)

def mesure_distance():
    TRIG.value(0); time.sleep_us(2)
    TRIG.value(1); time.sleep_us(10)
    TRIG.value(0)
    duree = time_pulse_us(ECHO, 1, 30000)
    if duree < 0:
        return None
    return (duree * 0.0343) / 2

# ---------- CAPTEURS IR ----------
ir_g = Pin(10, Pin.IN)
ir_d = Pin(11, Pin.IN)

def lire_ir():
    return (ir_g.value(), ir_d.value())

# ---------- SUIVI DE LIGNE ----------
def suivi_ligne(distance):
    global obstacle
    g, d = lire_ir()
    base_speed = 35000
    turn_speed = 20000

    if g == 1 and d == 1:
        avancer(distance, base_speed)
    elif g == 0 and d == 1:
        enA.duty_u16(turn_speed)
        enB.duty_u16(base_speed)
        in3.high(); in4.low(); in1.high(); in2.low()
        send_mqtt("Tourne", "Correction gauche", distance, obstacle)
    elif g == 1 and d == 0:
        enA.duty_u16(base_speed)
        enB.duty_u16(turn_speed)
        in3.high(); in4.low(); in1.high(); in2.low()
        send_mqtt("Tourne", "Correction droite", distance, obstacle)
    else:
        stop(distance)
        send_mqtt("Stop", "Croisement ou angle", distance, obstacle)

# ---------- BOUCLE PRINCIPALE ----------
print("Robot démarre : suivi de ligne + détection obstacle")

try:
    while True:
        client.check_msg()  # reçoit commandes MQTT

        if stop_requested:
            stop(0)
            stop_requested = False

        if not running:
            stop(0)
            time.sleep(0.1)
            continue

        d = mesure_distance()
        if d is None:
            continue

        # Vérifie obstacle
        if d < 15:  # seuil de sécurité
            obstacle = True
            print("🚧 Obstacle détecté à {:.1f}cm".format(d))
            stop(d)
            time.sleep(0.3)
            reculer(d)
            time.sleep(0.5)
            tourner_droite(d)
            time.sleep(0.6)
            stop(d)
        else:
            obstacle = False
            suivi_ligne(d)

        LED.toggle()
        time.sleep(0.05)

except KeyboardInterrupt:
    stop(0)
    print("Programme arrêté")
