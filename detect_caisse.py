import cv2
import numpy as np
import tflite_runtime.interpreter as tflite
import paho.mqtt.client as mqtt
import time

MODELS_PATH = "converted_tflite_quantized/"
LABELS_FILE = MODELS_PATH + "labels.txt"
MODEL_FILE = MODELS_PATH + "model.tflite"

# MQTT
MQTT_HOST = "localhost"
VISION_TOPIC = "robot/vision"
COMMAND_TOPIC = "robot/command"

client = mqtt.Client()
client.connect(MQTT_HOST, 1883, 60)
client.loop_start()

# Charger labels et modèle
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

while True:
    ret, frame = cap.read()
    if not ret:
        print("Problème caméra.")
        time.sleep(1)
        continue

    img = cv2.resize(frame, (width, height))
    img = np.expand_dims(img, axis=0).astype(np.uint8)
    interpreter.set_tensor(input_details[0]['index'], img)
    interpreter.invoke()
    output = interpreter.get_tensor(output_details[0]['index'])
    pred = np.argmax(output[0])
    label = labels[pred]

    # Publier le label détecté pour affichage web
    client.publish(VISION_TOPIC, label)

    # Afficher la détection en console
    print("Détection :", label)

    # Si caisse jaune ou bleue détectée : action robot
    if label.lower() in ["caisse jaune", "caisse bleue"]:
        current = time.time()
        # Eviter traitements multiples
        if etat_action != label or current - t_prev_action > 3:
            print("ACTION : stop/recul pour", label)
            client.publish(COMMAND_TOPIC, "stop")
            time.sleep(1)
            client.publish(COMMAND_TOPIC, "start")
            etat_action = label
            t_prev_action = current
    else:
        etat_action = None

    time.sleep(0.2)

cap.release()