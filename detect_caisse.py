import cv2
import numpy as np
import tflite_runtime.interpreter as tflite
import paho.mqtt.client as mqtt
import time

# --- CONFIGURATION ---
MODELS_PATH = "converted_tflite/"
LABELS_FILE = MODELS_PATH + "labels.txt"
MODEL_FILE = MODELS_PATH + "model_unquant.tflite"

MQTT_HOST = "localhost"

# Topic pour l'affichage web (Server.py) -> Feedback constant
TOPIC_DISPLAY = "robot/vision"

# Topic pour le contrôle moteur (Pico W) -> Actions ponctuelles
TOPIC_EVENT = "robot/vision_event"

# --- INIT MQTT ---
client = mqtt.Client()
client.connect(MQTT_HOST, 1883, 60)
client.loop_start()

# --- INIT IA ---
print("Chargement du modèle...")
with open(LABELS_FILE, "r") as f:
    # On nettoie les numéros (ex: "0 Caisse" -> "Caisse")
    labels = [line.strip().split(' ', 1)[1] for line in f]

interpreter = tflite.Interpreter(model_path=MODEL_FILE)
interpreter.allocate_tensors()
input_details = interpreter.get_input_details()
output_details = interpreter.get_output_details()
height, width = input_details[0]['shape'][1:3]

# --- INIT CAMERA ---
cap = cv2.VideoCapture(0)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 320) # Résolution réduite pour aller plus vite
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 240)
cap.set(cv2.CAP_PROP_FPS, 10) # Demande 10 FPS

print("Vision prête. Feedback constant activé.")

last_action_time = 0
COOLDOWN = 5.0 # Temps entre deux ACTIONS physiques (pas l'affichage)

try:
    while True:
        start_time = time.time()

        ret, frame = cap.read()
        if not ret:
            time.sleep(0.1)
            continue

        # Prétraitement
        img_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        img_resized = cv2.resize(img_rgb, (width, height))
        input_data = (np.float32(img_resized) - 127.5) / 127.5
        input_data = np.expand_dims(input_data, axis=0)

        # Inférence
        interpreter.set_tensor(input_details[0]['index'], input_data)
        interpreter.invoke()
        output = interpreter.get_tensor(output_details[0]['index'])[0]

        pred = np.argmax(output)
        confidence = output[pred]
        label = labels[pred]

        # --- 1. FEEDBACK CONSTANT (Pour server.py / Interface Web) ---
        # On envoie TOUT ce qu'on voit, même la "Route" ou une faible confiance
        msg_display = f"{label} ({confidence*100:.0f}%)"
        print(f"Vu: {msg_display}") # Affiche dans la console du Pi
        client.publish(TOPIC_DISPLAY, msg_display)

        # --- 2. DECLENCHEMENT ACTION (Pour Pico W) ---
        now = time.time()

        # Condition stricte pour bouger le robot : Forte confiance + Cooldown passé
        if confidence > 0.90 and (now - last_action_time > COOLDOWN):

            if "noire" in label.lower():
                print(">>> ACTION: CAISSE NOIRE")
                client.publish(TOPIC_EVENT, "CAISSE_NOIRE")
                last_action_time = now

            elif "bleue" in label.lower() or "jaune" in label.lower():
                print(">>> ACTION: CAISSE COULEUR")
                client.publish(TOPIC_EVENT, "CAISSE_COULEUR")
                last_action_time = now

        # Calcul FPS réel pour info
        elapsed = time.time() - start_time
        # On ne met pas de sleep artificiel ici pour maximiser les FPS
        # Si le Pi chauffe trop, décommenter la ligne suivante :
        # time.sleep(0.05)

except KeyboardInterrupt:
    print("Arrêt...")
finally:
    cap.release()
    client.loop_stop()
    client.disconnect()