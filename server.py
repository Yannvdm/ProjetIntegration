from flask import Flask, jsonify, send_from_directory, make_response
import threading, time, sys
import paho.mqtt.client as mqtt

app = Flask(__name__, static_url_path="", static_folder="static")

# ------- Etat partagé -------
state_lock = threading.Lock()
etat = "Initialisation"
last_manoeuvre = "—"
duty = 0
obstacle = False
ip = None
obstacle_message = ""  # Nouveau champ pour message obstacle
distance = None        # Variable globale pour distance capteur
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

def set_etat(new_state, manoeuvre=None, dist=None):
    global etat, last_manoeuvre, obstacle_message, distance
    changed = False
    with state_lock:
        if new_state != etat:
            changed = True
        etat = new_state
        if manoeuvre:
            last_manoeuvre = manoeuvre
        if dist is not None:
            distance = dist  # Mémorisation distance reçue
        if new_state.lower() == "stop" and dist is not None:
            obstacle_message = f"Obstacle à {dist:.1f} cm, changement de direction"
        elif new_state.lower() == "avance":
            obstacle_message = ""
    if changed:
        add_log(new_state)
        print(f"DEBUG set_etat called with: {new_state}, manoeuvre: {manoeuvre}, dist: {dist}")
        sys.stdout.flush()

def on_connect(client, userdata, flags, rc):
    add_log(f"MQTT connecté avec code {rc}")
    client.subscribe("robot/status")

def on_message(client, userdata, msg):
    import json
    try:
        payload = json.loads(msg.payload.decode())
        new_state = payload.get("etat")
        new_manoeuvre = payload.get("manoeuvre")
        dist = payload.get("distance")  # distance en cm, optionnel
        if new_state:
            set_etat(new_state, new_manoeuvre, dist)
            add_log(f"MQTT reçu état: {new_state}, manoeuvre: {new_manoeuvre}, distance: {dist}")
    except Exception as e:
        add_log(f"Erreur MQTT message: {e}")

mqtt_client = mqtt.Client()
mqtt_client.on_connect = on_connect
mqtt_client.on_message = on_message
mqtt_client.connect("localhost", 1883, 60)
mqtt_client.loop_start()

@app.after_request
def no_cache(resp):
    resp.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    resp.headers["Pragma"] = "no-cache"
    resp.headers["Expires"] = "0"
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
            "log": log[-20:],
            "ip": ip,
            "duty": duty,
            "obstacle": obstacle,
            "last": last_manoeuvre,
            "obstacle_message": obstacle_message,
            "distance": distance  # Ajout de la distance à la réponse JSON
        }
    resp = make_response(jsonify(payload))
    resp.headers["Cache-Control"] = "no-store"
    return resp

@app.get("/start")
def start():
    mqtt_client.publish("robot/command", "start")
    add_log("Commande MQTT: start")
    return jsonify(ok=True)

@app.get("/stop")
def stop():
    mqtt_client.publish("robot/command", "stop")
    add_log("Commande MQTT: stop")
    return jsonify(ok=True)

if __name__ == "__main__":
    add_log("Serveur Flask lancé")
    app.run(host="0.0.0.0", port=5000, debug=False, threaded=True)
