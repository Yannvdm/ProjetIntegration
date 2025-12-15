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
TOPIC_DISPLAY = "robot/vision"  # Feedback visuel
TOPIC_EVENT = "robot/vision_event"  # Action moteur

COOLDOWN = 5.0


# --- FONCTIONS TESTABLES (LOGIQUE PURE) ---

def load_model_and_labels(model_path, labels_path):
    """Charge le modèle TFLite et le fichier labels."""
    print("Chargement du modèle...")
    with open(labels_path, "r") as f:
        # On nettoie les numéros (ex: "0 Caisse" -> "Caisse")
        labels = [line.strip().split(' ', 1)[1] for line in f]

    interpreter = tflite.Interpreter(model_path=model_path)
    interpreter.allocate_tensors()
    return interpreter, labels


def preprocess_frame(frame, width, height):
    """Prépare l'image pour le modèle (Resize + Normalisation)."""
    img_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    img_resized = cv2.resize(img_rgb, (width, height))
    input_data = (np.float32(img_resized) - 127.5) / 127.5
    input_data = np.expand_dims(input_data, axis=0)
    return input_data


def predict(interpreter, input_data, labels):
    """Exécute l'inférence et retourne label + confiance."""
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
    # ... (Le début de la fonction reste identique : vérification cooldown et confiance) ...
    if confidence <= 0.90:
        return False, None

    if (current_time - last_action_time) <= COOLDOWN:
        return False, None

    # 2. Vérifier le type (MODIFICATIONS ICI)
    label_lower = label.lower()

    if "noire" in label_lower:
        return True, "CAISSE_NOIRE"

    elif "bleue" in label_lower or "jaune" in label_lower:
        return True, "CAISSE_COULEUR"

    # --- AJOUT DU NID ---
    elif "nid" in label_lower:
        return True, "ACTION_NID"

    return False, None


# --- EXECUTION PRINCIPALE (CELLE QUI TOURNE SUR LE ROBOT) ---
if __name__ == "__main__":
    # 1. Init MQTT
    client = mqtt.Client()
    client.connect(MQTT_HOST, 1883, 60)
    client.loop_start()

    # 2. Init IA
    interpreter, labels = load_model_and_labels(MODEL_FILE, LABELS_FILE)
    input_details = interpreter.get_input_details()
    height, width = input_details[0]['shape'][1:3]

    # 3. Init Camera
    cap = cv2.VideoCapture(0)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 320)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 240)
    cap.set(cv2.CAP_PROP_FPS, 10)

    print("Vision prête. Feedback constant activé.")
    last_action_time = 0

    try:
        while True:
            start_time = time.time()

            ret, frame = cap.read()
            if not ret:
                time.sleep(0.1)
                continue

            # --- Utilisation des fonctions isolées ---
            input_data = preprocess_frame(frame, width, height)
            label, confidence = predict(interpreter, input_data, labels)

            # --- 1. FEEDBACK CONSTANT (Web) ---
            msg_display = f"{label} ({confidence * 100:.0f}%)"
            print(f"Vu: {msg_display}")
            client.publish(TOPIC_DISPLAY, msg_display)

            # --- 2. LOGIQUE ACTION (Moteurs) ---
            now = time.time()
            do_action, msg_event = get_action_decision(label, confidence, last_action_time, now)

            if do_action:
                print(f">>> ACTION: {msg_event}")  # Debug Console
                client.publish(TOPIC_EVENT, msg_event)
                last_action_time = now


            elapsed = time.time() - start_time
            # time.sleep(0.05) # Décommenter si chauffe

    except KeyboardInterrupt:
        print("Arrêt...")
    finally:
        cap.release()
        client.loop_stop()
        client.disconnect()