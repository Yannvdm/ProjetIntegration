from flask import Flask, jsonify, send_from_directory, make_response
import threading, time, sys
import paho.mqtt.client as mqtt

app = Flask(__name__, static_url_path="", static_folder="static")

# ------- État partagé -------
state_lock = threading.Lock()
etat = "Initialisation"
last_manoeuvre = "—"
duty = 0
obstacle = False
ip = None
obstacle_message = ""
distance = None
vision_label = "—"
LOG_MAX = 100

log = []


def add_log(msg):
    t = time.time()
    with state_lock:
        log.append((t, msg))
        if len(log) > LOG_MAX:
            log.pop(0)
    print(f"[{time.strftime('%H:%M:%S')}] {msg}")
    sys.stdout.flush()


def set_etat(new_state, manoeuvre=None, dist=None, obs=False):
    global etat, last_manoeuvre, obstacle_message, distance, obstacle
    changed = False

    # Force le log pour les événements importants
    is_important = (new_state in ["Action", "Urgence"])

    with state_lock:
        if new_state != etat:
            changed = True

        etat = new_state
        if manoeuvre:
            last_manoeuvre = manoeuvre
        if dist is not None:
            distance = dist
        obstacle = obs

        if new_state.lower() == "stop" and dist is not None and obs:
            obstacle_message = f"Obstacle à {dist:.1f} cm"
        else:
            obstacle_message = ""

    # On log si l'état change OU si c'est une action importante (même répétée)
    if changed or is_important:
        msg_log = f"{new_state}"
        if manoeuvre: msg_log += f" ({manoeuvre})"
        add_log(msg_log)


def on_connect(client, userdata, flags, rc):
    add_log(f"MQTT connecté code {rc}")
    client.subscribe("robot/status")
    client.subscribe("robot/vision")


def on_message(client, userdata, msg):
    import json
    global vision_label
    try:
        if msg.topic == "robot/vision":
            vision_label = msg.payload.decode()
            # On ne log pas la vision en continu sinon ça spamme,
            # sauf si tu le veux vraiment (décommente la ligne suivante)
            # add_log(f"Vision: {vision_label}")

        elif msg.topic == "robot/status":
            payload = json.loads(msg.payload.decode())
            new_state = payload.get("etat")
            new_manoeuvre = payload.get("manoeuvre")
            dist = payload.get("distance")
            obs = payload.get("obstacle", False)
            if new_state:
                set_etat(new_state, new_manoeuvre, dist, obs)
    except Exception as e:
        print(f"Erreur decode MQTT: {e}")


mqtt_client = mqtt.Client()
mqtt_client.on_connect = on_connect
mqtt_client.on_message = on_message
mqtt_client.connect("localhost", 1883, 60)
mqtt_client.loop_start()


@app.after_request
def no_cache(resp):
    resp.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    return resp


@app.get("/")
def root():
    return send_from_directory("static", "index.html")


@app.get("/status")
def status():
    with state_lock:
        payload = {
            "etat": etat,
            "ts": time.time(),
            "log": log[-20:],  # Envoie les 20 derniers logs
            "ip": ip,
            "obstacle": obstacle,
            "last": last_manoeuvre,
            "obstacle_message": obstacle_message,
            "distance": distance,
            "vision_label": vision_label
        }
    return jsonify(payload)


if __name__ == "__main__":
    add_log("Serveur Flask lancé")
    app.run(host="0.0.0.0", port=5000, debug=False, threaded=True)