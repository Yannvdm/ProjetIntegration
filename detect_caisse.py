import cv2
import numpy as np
import tflite_runtime.interpreter as tflite
import time
import paho.mqtt.client as mqtt

# --- CONFIGURATION ---
MODELS_PATH = "converted_tflite/"
LABELS_FILE = MODELS_PATH + "labels.txt"
MODEL_FILE = MODELS_PATH + "model_unquant.tflite"

MQTT_HOST = "localhost"
TOPIC_DISPLAY = "robot/vision"
TOPIC_EVENT = "robot/vision_event"

COOLDOWN = 5.0


# --- FONCTIONS ---

def load_model_and_labels(model_path, labels_path):
    print("Chargement du modèle...")
    with open(labels_path, "r") as f:
        # On ne garde que le texte après le numéro (ex: "0 Caisse jaune" -> "Caisse jaune")
        labels = [line.strip().split(' ', 1)[1] for line in f]

    interpreter = tflite.Interpreter(model_path=model_path)
    interpreter.allocate_tensors()
    return interpreter, labels


def preprocess_frame(frame, width, height):
    img_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    img_resized = cv2.resize(img_rgb, (width, height))
    input_data = (np.float32(img_resized) - 127.5) / 127.5
    input_data = np.expand_dims(input_data, axis=0)
    return input_data


def predict(interpreter, input_data, labels):
    input_details = interpreter.get_input_details()
    output_details = interpreter.get_output_details()

    interpreter.set_tensor(input_details[0]['index'], input_data)
    interpreter.invoke()
    output = interpreter.get_tensor(output_details[0]['index'])[0]

    pred = np.argmax(output)
    confidence = output[pred]
    label = labels[pred]
    return label, confidence


def get_action_decision(label, confidence, last_action_time, current_time):
    # 1. Seuil de confiance (abaissé à 0.85 pour être plus tolérant)
    if confidence <= 0.85:
        return False, None

    # 2. Cooldown (anti-spam)
    if (current_time - last_action_time) <= COOLDOWN:
        return False, None

    # 3. Logique spécifique aux labels donnés
    # Labels attendus : "Caisse jaune", "Caisse bleue", "Caisse noire", "Route", "Nid"
    label_lower = label.lower()

    if "route" in label_lower:
        # Pas d'action pour la route
        return False, None

    elif "noire" in label_lower:
        return True, "CAISSE_NOIRE"

    elif "bleue" in label_lower or "jaune" in label_lower:
        # Même action pour bleue et jaune
        return True, "CAISSE_COULEUR"

    elif "nid" in label_lower:
        return True, "ACTION_NID"

    return False, None


# --- MAIN ---
if __name__ == "__main__":
    client = mqtt.Client()
    client.connect(MQTT_HOST, 1883, 60)
    client.loop_start()

    interpreter, labels = load_model_and_labels(MODEL_FILE, LABELS_FILE)
    input_details = interpreter.get_input_details()
    height, width = input_details[0]['shape'][1:3]

    cap = cv2.VideoCapture(0)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 320)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 240)
    cap.set(cv2.CAP_PROP_FPS, 10)

    print("Vision prête. Feedback activé.")
    last_action_time = 0

    try:
        while True:
            start_time = time.time()
            ret, frame = cap.read()
            if not ret:
                time.sleep(0.1)
                continue

            input_data = preprocess_frame(frame, width, height)
            label, confidence = predict(interpreter, input_data, labels)

            # Envoi pour affichage Web
            msg_display = f"{label} ({confidence * 100:.0f}%)"
            print(f"Vu: {msg_display}")
            client.publish(TOPIC_DISPLAY, msg_display)

            # Décision Moteur
            now = time.time()
            do_action, msg_event = get_action_decision(label, confidence, last_action_time, now)

            if do_action:
                print(f">>> envoi ACTION MQTT: {msg_event}")
                client.publish(TOPIC_EVENT, msg_event)
                last_action_time = now

            # time.sleep(0.05) # Décommenter si le Pi chauffe trop

    except KeyboardInterrupt:
        print("Arrêt...")
    finally:
        cap.release()
        client.loop_stop()
        client.disconnect()