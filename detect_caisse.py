import cv2
import numpy as np
import tflite_runtime.interpreter as tflite
import paho.mqtt.client as mqtt
import time

MODELS_PATH = "converted_tflite/"
LABELS_FILE = MODELS_PATH + "labels.txt"
MODEL_FILE = MODELS_PATH + "model_unquant.tflite"

# MQTT
MQTT_HOST = "localhost"          # ou IP du broker
VISION_TOPIC = "robot/vision"
COMMAND_TOPIC = "robot/command"

client = mqtt.Client()
client.connect(MQTT_HOST, 1883, 60)
client.loop_start()

# Charger labels et modèle
print("Chargement du modèle...")
with open(LABELS_FILE, "r") as f:
    labels = [line.strip().split(' ', 1)[1] for line in f]

interpreter = tflite.Interpreter(model_path=MODEL_FILE)
interpreter.allocate_tensors()

input_details = interpreter.get_input_details()
output_details = interpreter.get_output_details()
height, width = input_details[0]['shape'][1:3]

# Boucle principale
etat_action = None
t_prev_action = 0

cap = cv2.VideoCapture(0)
print("Détection caisse démarrée...")

try:
    while True:
        ret, frame = cap.read()
        if not ret:
            print("Problème caméra.")
            time.sleep(1)
            continue

        # --- CORRECTION 1 : Conversion BGR vers RGB ---
        # OpenCV capture en BGR, mais Teachable Machine a appris en RGB.
        img_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        # Redimensionnement à la taille attendue par le modèle (ex: 224x224)
        img_resized = cv2.resize(img_rgb, (width, height))

        # --- CORRECTION 2 : Normalisation (-1 à 1) ---
        # Teachable Machine utilise (image - 127.5) / 127.5
        input_data = (np.float32(img_resized) - 127.5) / 127.5
        
        # Ajouter la dimension du batch (1, 224, 224, 3)
        input_data = np.expand_dims(input_data, axis=0)

        # Envoi au modèle
        interpreter.set_tensor(input_details[0]['index'], input_data)
        interpreter.invoke()

        # Récupération du résultat
        output = interpreter.get_tensor(output_details[0]['index'])[0]
        pred = np.argmax(output)
        confidence = output[pred]  # probabilité du label prédit
        label = labels[pred]

        print(f"Détection : {label} ({confidence*100:.1f}%)")
        client.publish(VISION_TOPIC, label)

        # Logique de déclenchement (Seulement si confiance >= 0.9)
        if confidence >= 0.9 and label.lower() in ["caisse noire"]:
            current = time.time()
            if etat_action != label or current - t_prev_action > 3:
                print("ACTION : stop/recul pour", label)
                client.publish(COMMAND_TOPIC, "stop")
                time.sleep(1)
                client.publish(COMMAND_TOPIC, "start")
                etat_action = label
                t_prev_action = current
        else:
            etat_action = None

        time.sleep(0.1)

except KeyboardInterrupt:
    print("Arrêt du programme...")

finally:
    cap.release()
    client.loop_stop()
    client.disconnect()
