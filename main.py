from machine import Pin, PWM, time_pulse_us
import time

# ===============================
# ===   CONFIGURATION MOTEURS  ===
# ===============================
# --- Moteur gauche ---
enA = PWM(Pin(0))
in3 = Pin(2, Pin.OUT)
in4 = Pin(1, Pin.OUT)

# --- Moteur droit ---
enB = PWM(Pin(3))
in1 = Pin(4, Pin.OUT)
in2 = Pin(6, Pin.OUT)

# Fréquence PWM et vitesse
enA.freq(1000)
enB.freq(1000)
VITESSE = 40000

def stop():
    enA.duty_u16(0)
    enB.duty_u16(0)
    in1.low(); in2.low()
    in3.low(); in4.low()

def avancer(vitesse=VITESSE):
    in3.high(); in4.low()
    in1.high(); in2.low()
    enA.duty_u16(vitesse)
    enB.duty_u16(vitesse)

def reculer(vitesse=VITESSE):
    in3.low(); in4.high()
    in1.low(); in2.high()
    enA.duty_u16(vitesse)
    enB.duty_u16(vitesse)

def tourner_gauche(vitesse=VITESSE):
    in3.low(); in4.high()
    in1.high(); in2.low()
    enA.duty_u16(vitesse)
    enB.duty_u16(vitesse)

def tourner_droite(vitesse=VITESSE):
    in3.high(); in4.low()
    in1.low(); in2.high()
    enA.duty_u16(vitesse)
    enB.duty_u16(vitesse)


# ===============================
# ===   CONFIGURATION CAPTEUR  ===
# ===============================
TRIG = Pin(7, Pin.OUT)
ECHO = Pin(8, Pin.IN)
LED = Pin(25, Pin.OUT)

def mesure_distance():
    TRIG.value(0)
    time.sleep_us(2)
    TRIG.value(1)
    time.sleep_us(10)
    TRIG.value(0)

    duree = time_pulse_us(ECHO, 1, 30000)  # 30 ms = ~5 m
    if duree < 0:
        return None
    distance = (duree * 0.0343) / 2
    return distance


# ===============================
# ===     PROGRAMME PRINCIPAL  ===
# ===============================
print("Robot démarré : détection d'obstacles à 20 cm")

try:
    while True:
        d = mesure_distance()
        if d is None:
            print("Aucune mesure (timeout)")
            continue

        print("Distance : {:.1f} cm".format(d))
        LED.toggle()

        if d < 20:
            print("Obstacle détecté à {:.1f} cm -> demi-tour".format(d))
            stop()
            time.sleep(0.2)
            reculer()
            time.sleep(0.5)
            tourner_droite()  # ou tourner_gauche()
            time.sleep(1.2)    # à ajuster pour ~180°
            stop()
            time.sleep(0.3)
        else:
            avancer()

        time.sleep(0.1)

except KeyboardInterrupt:
    stop()
    print("\nProgramme arrêté par l'utilisateur.")
