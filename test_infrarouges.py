from machine import Pin
import time

#CAPTEURS IR
ir_g = Pin(10, Pin.IN)   # Capteur gauche
ir_d = Pin(11, Pin.IN)   # Capteur droit
led = Pin(25, Pin.OUT)   # LED intégrée pour signal visuel

print("=== TEST CAPTEURS DE SUIVI DE LIGNE ===")
print("Place ton robot au-dessus de la ligne et observe les messages.\n")
print("Valeurs possibles :")
print("  - 0 = blanc / pas de ligne")
print("  - 1 = noir / ligne détectée\n")

try:
    while True:
        g = ir_g.value()
        d = ir_d.value()

        # Affiche les états bruts
        print("Gauche:", g, " | Droite:", d, end=" -> ")

        # Interprétation
        if g == 1 and d == 0:
            print("➡️ Ligne détectée à GAUCHE → tourne à gauche")
        elif g == 0 and d == 1:
            print("⬅️ Ligne détectée à DROITE → tourne à droite")
        elif g == 1 and d == 1:
            print("⬛ Ligne sous les DEUX capteurs")
        else:
            print("⬜ Aucun capteur sur la ligne (fond blanc)")

        # LED clignote à chaque lecture
        led.toggle()

        time.sleep(0.3)

except KeyboardInterrupt:
    print("\nTest arrêté manuellement.")

