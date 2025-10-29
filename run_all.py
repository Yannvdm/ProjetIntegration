import subprocess
import sys

# Optionnel : active le venv dans le shell, si besoin (sinon lance-le depuis le venv déjà activé)

# Lance server.py
server = subprocess.Popen([sys.executable, "server.py"])

# Lance detect_caisse.py
detect = subprocess.Popen([sys.executable, "detect_caisse.py"])

try:
    server.wait()
    detect.wait()
except KeyboardInterrupt:
    print("Arrêt manuel des scripts")
    server.terminate()
    detect.terminate()