from machine import Pin, PWM
import time

# --- Moteur gauche ---
enA = PWM(Pin(0))     # PWM moteur gauche
in3 = Pin(2, Pin.OUT)
in4 = Pin(1, Pin.OUT)

# --- Moteur droit ---
enB = PWM(Pin(3))     # PWM moteur droit
in1 = Pin(4, Pin.OUT)
in2 = Pin(6, Pin.OUT)

# Configuration PWM (fréquence standard ~1 kHz)
enA.freq(1000)
enB.freq(1000)

# Vitesse par défaut (duty cycle : 0-65535)
VITESSE = 40000

def stop():
    """Arrête complètement les moteurs"""
    enA.duty_u16(0)
    enB.duty_u16(0)
    in1.low(); in2.low()
    in3.low(); in4.low()

def avancer(vitesse=VITESSE):
    """Fait avancer le robot"""
    stop()
    in3.high(); in4.low()   # moteur gauche en avant
    in1.high(); in2.low()   # moteur droit en avant
    enA.duty_u16(vitesse)
    enB.duty_u16(vitesse)

def reculer(vitesse=VITESSE):
    """Fait reculer le robot"""
    stop()
    in3.low(); in4.high()   # moteur gauche en arrière
    in1.low(); in2.high()   # moteur droit en arrière
    enA.duty_u16(vitesse)
    enB.duty_u16(vitesse)

def tourner_gauche(vitesse=VITESSE):
    """Tourne sur place vers la gauche"""
    stop()
    in3.low(); in4.high()   # moteur gauche en arrière
    in1.high(); in2.low()   # moteur droit en avant
    enA.duty_u16(vitesse)
    enB.duty_u16(vitesse)

def tourner_droite(vitesse=VITESSE):
    """Tourne sur place vers la droite"""
    stop()
    in3.high(); in4.low()   # moteur gauche en avant
    in1.low(); in2.high()   # moteur droit en arrière
    enA.duty_u16(vitesse)
    enB.duty_u16(vitesse)


# --- Exemple de test ---
while True:
    print("Avancer")
    avancer()
    time.sleep(2)

    print("Stop")
    stop()
    time.sleep(1)

    print("Reculer")
    reculer()
    time.sleep(2)

    print("Stop")
    stop()
    time.sleep(1)

    print("Tourner 180°")
    tourner_droite()   # ou tourner_gauche()
    time.sleep(1.2)    # <-- à calibrer pour ~180°
    stop()
    time.sleep(1)
