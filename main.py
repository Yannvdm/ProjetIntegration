from machine import Pin, PWM, time_pulse_us
import time

#MOTEURS
enA = PWM(Pin(0))  # moteur gauche
in3 = Pin(2, Pin.OUT)
in4 = Pin(1, Pin.OUT)
enB = PWM(Pin(3))  # moteur droit
in1 = Pin(4, Pin.OUT)
in2 = Pin(6, Pin.OUT)

enA.freq(1000)
enB.freq(1000)

VITESSE_BASE = 30000     # vitesse globale réduite pour plus de contrôle
VITESSE_CORR = 18000     # vitesse côté lent pour correction
VITESSE_VIRAGE = 25000   # vitesse pour virage prolongé

def stop():
    enA.duty_u16(0)
    enB.duty_u16(0)
    in1.low(); in2.low()
    in3.low(); in4.low()

def avancer(vitesse=VITESSE_BASE):
    in3.high(); in4.low()  # gauche avant
    in1.high(); in2.low()  # droite avant
    enA.duty_u16(vitesse)
    enB.duty_u16(vitesse)

def reculer(vitesse=VITESSE_BASE):
    in3.low(); in4.high()
    in1.low(); in2.high()
    enA.duty_u16(vitesse)
    enB.duty_u16(vitesse)

def tourner_gauche_on_spot(vitesse=VITESSE_BASE):
    in3.low(); in4.high()
    in1.high(); in2.low()
    enA.duty_u16(vitesse)
    enB.duty_u16(vitesse)

def tourner_droite_on_spot(vitesse=VITESSE_BASE):
    in3.high(); in4.low()
    in1.low(); in2.high()
    enA.duty_u16(vitesse)
    enB.duty_u16(vitesse)

#CAPTEUR ULTRASON
TRIG = Pin(7, Pin.OUT)
ECHO = Pin(8, Pin.IN)
LED = Pin(25, Pin.OUT)

def mesure_distance():
    TRIG.value(0)
    time.sleep_us(2)
    TRIG.value(1)
    time.sleep_us(10)
    TRIG.value(0)
    duree = time_pulse_us(ECHO, 1, 30000)
    if duree < 0:
        return None
    return (duree * 0.0343) / 2

#CAPTEURS IR
ir_g = Pin(10, Pin.IN)
ir_d = Pin(11, Pin.IN)

def lire_ir():
    return (ir_g.value(), ir_d.value())

#SUIVI DE LIGNE
compteur_gauche = 0
compteur_droite = 0
NB_CYCLES_VIRAGE = 3  # nombre de cycles pour déclencher virage fort

def suivi_ligne():
    global compteur_gauche, compteur_droite
    g, d = lire_ir()

    # 1 = noir = ligne détectée
    if g == 0 and d == 0:
        # ligne entre les capteurs → avancer tout droit
        avancer(VITESSE_BASE)
        compteur_gauche = 0
        compteur_droite = 0
        print("G=0 D=0 → ligne centrée → avancer")

    elif g == 1 and d == 0:
        compteur_gauche += 1
        compteur_droite = 0
        if compteur_gauche >= NB_CYCLES_VIRAGE:
            # virage prolongé → rotation plus forte
            tourner_gauche_on_spot(VITESSE_VIRAGE)
            print("G=1 D=0 → virage fort gauche")
        else:
            # correction douce
            in3.high(); in4.low()
            in1.high(); in2.low()
            enA.duty_u16(VITESSE_BASE)
            enB.duty_u16(VITESSE_CORR)
            print("G=1 D=0 → correction gauche")

    elif g == 0 and d == 1:
        compteur_droite += 1
        compteur_gauche = 0
        if compteur_droite >= NB_CYCLES_VIRAGE:
            tourner_droite_on_spot(VITESSE_VIRAGE)
            print("G=0 D=1 → virage fort droite")
        else:
            # correction douce
            in3.high(); in4.low()
            in1.high(); in2.low()
            enA.duty_u16(VITESSE_CORR)
            enB.duty_u16(VITESSE_BASE)
            print("G=0 D=1 → correction droite")

    elif g == 1 and d == 1:
        # ligne large ou croisement → stop pour sécurité
        stop()
        compteur_gauche = 0
        compteur_droite = 0
        print("G=1 D=1 → ligne sous les deux capteurs → stop")

    else:
        stop()
        compteur_gauche = 0
        compteur_droite = 0
        print("État IR inattendu :", g, d, "→ stop")

#BOUCLE PRINCIPALE
print("Robot démarre : suivi de ligne + détection obstacle")

try:
    while True:
        dist = mesure_distance()
        if dist is None:
            suivi_ligne()
            LED.toggle()
            time.sleep(0.05)
            continue

        if dist < 15:
            print("🚧 Obstacle détecté à {:.1f} cm".format(dist))
            stop()
            time.sleep(0.25)
            reculer(28000)
            time.sleep(0.45)
            tourner_droite_on_spot(30000)
            time.sleep(0.55)
            stop()
            time.sleep(0.2)
        else:
            suivi_ligne()

        LED.toggle()
        time.sleep(0.05)

except KeyboardInterrupt:
    stop()
    print("Programme arrêté manuellement")

