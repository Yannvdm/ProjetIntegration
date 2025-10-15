from flask import Flask, jsonify, send_from_directory, make_response
import threading, time, random, sys
import paho.mqtt.client as mqtt

app = Flask(__name__, static_url_path="", static_folder="static")

# ------- Etat partagé -------
state_lock = threading.Lock()
etat = "Initialisation"
last_manoeuvre = "—"
duty = 0
obstacle = False
ip = None
run_enabled = True
LOG_MAX = 100

log = []

def add_log(msg):
    t = time.time()
    with state_lock:
        log.append((t, msg))
        if len(log) > LOG_MAX:
            log.pop(0)
    print(f"[{time.strftime('%H:%M:%S')}] {msg}"); sys.stdout.flush()

def set_etat(new_state, manoeuvre=None):
    global etat, last_manoeuvre
    changed = False
    with state_lock:
        if new_state != etat:
            changed = True
        etat = new_state
        if manoeuvre:
            last_manoeuvre = manoeuvre
    if changed:
        add_log(new_state)
        print(f"DEBUG set_etat called with: {new_state}, manoeuvre: {manoeuvre}")
        sys.stdout.flush()

def autonomy_loop():
    global duty, obstacle, last_manoeuvre

    V_AV, V_RECU, V_TOUR = 38000, 22000, 24000
    duty_target = 0
    last_state_change = time.monotonic()
    random.seed()

    add_log("Autonomie – démarrage")

    TICK = 0.05          # 20 Hz
    RAMP = 1500          # pas de duty par tick

    while True:
        start = time.monotonic()

        if not run_enabled:
            duty_target = 0
            set_etat("Stop", "Arrêt")
            time.sleep(TICK)
            continue

        # Choix aléatoire pondéré
        r = random.random()
        if r < 0.30:
            # Avance (30%)
            set_etat("Avance", "Avancer")
            duty_target = V_AV
        elif r < 0.45:
            # Tourne gauche (15%)
            set_etat("Tourne gauche", "Tourner à gauche")
            duty_target = V_TOUR
        elif r < 0.60:
            # Tourne droite (15%)
            set_etat("Tourne droite", "Tourner à droite")
            duty_target = V_TOUR
        elif r < 0.80:
            # Freine (20%)
            set_etat("Freinage", "Freinage")
            duty_target = 0
        else:
            # Recul (20%)
            set_etat("Reculer", "Reculer")
            duty_target = V_RECU

        # Rampe du duty pour transition fluide
        with state_lock:
            if duty < duty_target:
                duty = min(duty + RAMP, duty_target)
            elif duty > duty_target:
                duty = max(duty - RAMP, duty_target)

        elapsed = time.monotonic() - start
        sleep_left = TICK - elapsed
        if sleep_left > 0:
            time.sleep(sleep_left)

# -------- MQTT Client --------
def on_connect(client, userdata, flags, rc):
    add_log(f"MQTT connecté avec code {rc}")
    client.subscribe("robot/status")

def on_message(client, userdata, msg):
    # Exemple, on attend un payload JSON contenant etat et manoeuvre
    import json
    try:
        payload = json.loads(msg.payload.decode())
        new_state = payload.get("etat")
        new_manoeuvre = payload.get("manoeuvre")
        if new_state:
            set_etat(new_state, new_manoeuvre)
            add_log(f"MQTT reçu état: {new_state}, manoeuvre: {new_manoeuvre}")
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
            "last": last_manoeuvre
        }
    resp = make_response(jsonify(payload))
    resp.headers["Cache-Control"] = "no-store"
    return resp

@app.get("/start")
def start():
    global run_enabled
    run_enabled = True
    add_log("RUN = True (start)")
    return jsonify(ok=True)

@app.get("/stop")
def stop():
    global run_enabled
    run_enabled = False
    add_log("RUN = False (stop)")
    return jsonify(ok=True)


if __name__ == "__main__":
    add_log("Serveur Flask lancé")
    threading.Thread(target=autonomy_loop, daemon=True).start()
    app.run(host="0.0.0.0", port=5000, debug=False, threaded=True)
