import network
import socket
import time
import _thread
import ujson as json
from machine import Pin, PWM

# --- MOTEURS (ta config) ---
enA = PWM(Pin(0))
in3 = Pin(2, Pin.OUT)
in4 = Pin(1, Pin.OUT)

enB = PWM(Pin(3))
in1 = Pin(4, Pin.OUT)
in2 = Pin(6, Pin.OUT)

enA.freq(1000)
enB.freq(1000)
VITESSE = 40000

def stop():
    enA.duty_u16(0)
    enB.duty_u16(0)
    in1.low(); in2.low()
    in3.low(); in4.low()

def avancer(vitesse=VITESSE):
    stop()
    in3.high(); in4.low()
    in1.high(); in2.low()
    enA.duty_u16(vitesse)
    enB.duty_u16(vitesse)

def reculer(vitesse=VITESSE):
    stop()
    in3.low(); in4.high()
    in1.low(); in2.high()
    enA.duty_u16(vitesse)
    enB.duty_u16(vitesse)

def tourner_gauche(vitesse=VITESSE):
    stop()
    in3.low(); in4.high()
    in1.high(); in2.low()
    enA.duty_u16(vitesse)
    enB.duty_u16(vitesse)

def tourner_droite(vitesse=VITESSE):
    stop()
    in3.high(); in4.low()
    in1.low(); in2.high()
    enA.duty_u16(vitesse)
    enB.duty_u16(vitesse)

# --- ETAT GLOBAL + journal (thread-safe avec _thread) ---
etat = "Initialisation"
log = []  # liste de (timestamp, message)
_state_lock = _thread.allocate_lock()

def add_log(msg):
    t = time.time()
    _state_lock.acquire()
    try:
        log.append((t, msg))
        # limite taille log
        if len(log) > 100:
            log.pop(0)
    finally:
        _state_lock.release()

def set_etat(new):
    global etat
    _state_lock.acquire()
    try:
        etat = new
        add_log(new)
    finally:
        _state_lock.release()

# --- PAGE HTML (client-side polling) ---
html_page = """<!doctype html>
<html>
<head>
<meta charset="utf-8">
<title>Robot autonome - Statut</title>
<style>
body { font-family: Arial, sans-serif; text-align:center; padding:20px; }
.badge { display:inline-block; padding:10px 16px; border-radius:8px; font-weight:700; }
#etat { font-size: 24px; margin: 12px 0; }
#log { width:90%%; max-width:700px; margin: 10px auto; text-align:left; height:200px; overflow:auto; border:1px solid #ddd; padding:8px; background:#fafafa; }
</style>
</head>
<body>
<h1>Statut du robot</h1>
<div>Action actuelle : <span id="etat" class="badge">?</span></div>
<div>Dernière mise à jour : <span id="maj">-</span></div>
<h3>Journal (récent)</h3>
<div id="log">Chargement...</div>

<script>
async function update(){
  try{
    let r = await fetch('/status');
    if(!r.ok) { throw "HTTP " + r.status; }
    let data = await r.json();
    document.getElementById('etat').innerText = data.etat;
    let d = new Date(data.ts*1000);
    document.getElementById('maj').innerText = d.toLocaleTimeString();
    // log
    let out = '';
    data.log.forEach(function(item){
      let t = new Date(item[0]*1000).toLocaleTimeString();
      out += '['+t+'] '+item[1] + '<br>';
    });
    document.getElementById('log').innerHTML = out;
  } catch(e){
    document.getElementById('etat').innerText = "ERREUR";
    document.getElementById('log').innerText = "Impossible de joindre le Pico: " + e;
  }
}
// 600ms polling (ajuste si besoin)
setInterval(update, 600);
update();
</script>
</body>
</html>
"""

# --- SERVEUR HTTP dans un thread séparé ---
def http_server(wlan_ip):
    addr = socket.getaddrinfo('0.0.0.0', 80)[0][-1]
    s = socket.socket()
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind(addr)
    s.listen(1)
    print("Serveur HTTP démarré sur http://%s" % wlan_ip)
    while True:
        try:
            cl, addr = s.accept()
            # lecture requête
            cl_file = cl.makefile('rwb', 0)
            request_line = cl_file.readline()
            if not request_line:
                cl.close(); continue
            request_line = request_line.decode('utf-8')
            # vider headers
            while True:
                header = cl_file.readline()
                if not header or header == b'\r\n':
                    break
            # extraire chemin
            try:
                method, path, proto = request_line.split()
            except:
                cl.close(); continue

            if path == '/' or path.startswith('/index'):
                cl.send('HTTP/1.0 200 OK\r\nContent-type: text/html\r\n\r\n')
                cl.send(html_page)
            elif path.startswith('/status'):
                # renvoyer JSON avec etat, timestamp et les derniers logs (ex: 20)
                _state_lock.acquire()
                try:
                    data = {
                        'etat': etat,
                        'ts': time.time(),
                        'log': log[-20:]
                    }
                finally:
                    _state_lock.release()
                payload = json.dumps(data)
                cl.send('HTTP/1.0 200 OK\r\nContent-type: application/json\r\n\r\n')
                cl.send(payload)
            else:
                cl.send('HTTP/1.0 404 NOT FOUND\r\nContent-type: text/plain\r\n\r\n')
                cl.send('404')
            cl.close()
        except Exception as e:
            try:
                cl.close()
            except:
                pass
            print("Erreur serveur:", e)

# --- Connexion Wi-Fi (STA) ---
ssid = "TonSSID"
password = "TonMOTDEPASSE"

wlan = network.WLAN(network.STA_IF)
wlan.active(True)
wlan.connect(ssid, password)
print("Connexion WiFi...")
while not wlan.isconnected():
    time.sleep(0.5)
ip = wlan.ifconfig()[0]
print("Connecté, IP =", ip)
add_log("Connecté au WiFi: " + ip)

# lancer serveur HTTP en thread
_thread.start_new_thread(http_server, (ip,))

# --- Détection d'obstacle (placeholder) ---
# Si tu as un capteur ultrason (HC-SR04) ou capteurs IR, tu peux implémenter detect_obstacle() ici.
# Exemple simple (placeholder) : retourne False par défaut.
def detect_obstacle():
    # TODO: remplacer par lecture de capteur (True si obstacle proche)
    return False

# --- Boucle d'autonomie (exemple simple) ---
set_etat("Autonome - démarrage")
time.sleep(0.5)

try:
    while True:
        # Comportement simple : avancer, si obstacle -> manœuvre d'évitement
        if detect_obstacle():
            set_etat("Obstacle détecté - freinage")
            stop()
            time.sleep(0.1)
            set_etat("Reculer (éviter)")
            reculer(VITESSE//2)
            time.sleep(0.5)
            set_etat("Tourne droite (éviter)")
            tourner_droite(VITESSE//2)
            time.sleep(0.6)
            stop()
            time.sleep(0.1)
        else:
            # avancer tant que pas d'obstacle
            _state_lock.acquire()
            try:
                if etat != "Avance":
                    etat = "Avance"
                    add_log(etat)
            finally:
                _state_lock.release()
            avancer()
            # petite pause pour laisser the webserver tourner et pour réduire CPU
            time.sleep(0.12)

except Exception as e:
    set_etat("Erreur autonome: " + str(e))
    stop()
    raise
