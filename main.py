from machine import Pin, PWM, time_pulse_us
import time
import network
from umqtt.simple import MQTTClient
import ujson

# Config Wi-Fi
SSID = "CharlesRed13"
PASS = "123456789"
wlan = network.WLAN(network.STA_IF)
wlan.active(True)
wlan.connect(SSID, PASS)
while not wlan.isconnected():
    time.sleep(1)
print("Connecté, IP:", wlan.ifconfig()[0])

# Config MQTT
MQTT_SERV = "10.171.184.167"
MQTT_TOPIC = "robot/status"
CLIENT_ID = "pico_robot"
client = MQTTClient(CLIENT_ID, MQTT_SERV)
client.connect()

# Flag pour le contrôle
running = True  # Par défaut, le robot tourne
stop_requested = False

def sub_cb(topic, msg):
    global running, stop_requested
    print("Commande reçue:", topic, msg)
    if msg == b'stop':
        running = False
        stop_requested = True  # marque le changement pour l'action hors callback
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
    except OSError:
        try:
            client.disconnect()
        except:
            pass
        try:
            client.connect()
            client.subscribe(b"robot/command")
            client.publish(MQTT_TOPIC, msg)
        except Exception as e:
            print("Erreur MQTT:", e)

# Moteurs
enA = PWM(Pin(0)); in3 = Pin(2, Pin.OUT); in4 = Pin(1, Pin.OUT)
enB = PWM(Pin(3)); in1 = Pin(4, Pin.OUT); in2 = Pin(6, Pin.OUT)
enA.freq(1000); enB.freq(1000); VITESSE = 40000

# Mesure distance
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

# Fonctions déplacement
def stop(distance):
    send_mqtt("Stop", "Arrêt", distance, obstacle)
    enA.duty_u16(0); enB.duty_u16(0)
    in1.low(); in2.low(); in3.low(); in4.low()

def avancer(distance, vitesse=VITESSE):
    global obstacle
    obstacle = False
    in3.high(); in4.low(); in1.high(); in2.low()
    enA.duty_u16(vitesse); enB.duty_u16(vitesse)
    send_mqtt("Avance", "Avancer", distance, obstacle)

def reculer(distance, vitesse=VITESSE):
    global obstacle
    obstacle = False
    in3.low(); in4.high(); in1.low(); in2.high()
    enA.duty_u16(vitesse); enB.duty_u16(vitesse)
    send_mqtt("Recul", "Reculer", distance, obstacle)

def tourner_gauche(distance, vitesse=VITESSE):
    global obstacle
    obstacle = False
    in3.low(); in4.high(); in1.high(); in2.low()
    enA.duty_u16(vitesse); enB.duty_u16(vitesse)
    send_mqtt("Tourne", "Tourner gauche", distance, obstacle)

def tourner_droite(distance, vitesse=VITESSE):
    global obstacle
    obstacle = False
    in3.high(); in4.low(); in1.low(); in2.high()
    enA.duty_u16(vitesse); enB.duty_u16(vitesse)
    send_mqtt("Tourne", "Tourner droite", distance, obstacle)

# Boucle principale
print("Robot démarre : détection obstacle à 20cm")
try:
    while True:
        # Vérifie commandes MQTT
        try:
            client.check_msg()
        except OSError as e:
            print("Erreur MQTT check_msg:", e)
            try: client.disconnect()
            except: pass
            time.sleep(1)
            try:
                client.connect()
                client.subscribe(b"robot/command")
            except Exception as e2:
                print("Reconnexion MQTT échouée:", e2)

        # Si arrêt demandé
        if stop_requested:
            stop(0)
            stop_requested = False
        # Si pas en marche: ne pas déplacer
        if not running:
            stop(0)
            time.sleep(0.2)
            continue

        # Mesure distance
        d = mesure_distance()
        if d is None:
            print("Aucune mesure (timeout)")
            continue
        print("Distance : {:.1f}cm".format(d))
        LED.toggle()

        # Détection obstacle
        if d < 20:
            obstacle = True
            print("Obstacle détecté à {:.1f}cm".format(d))
            stop(d)
            time.sleep(0.2)
            reculer(d)
            time.sleep(0.5)
            tourner_droite(d)
            time.sleep(1.2)
            stop(d)
            time.sleep(0.3)
        else:
            obstacle = False
            avancer(d)

        time.sleep(0.2)

except KeyboardInterrupt:
    stop(d)
    print("Programme arrêté")

