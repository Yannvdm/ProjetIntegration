import unittest
import sys
from unittest.mock import MagicMock

# --- ASTUCE DE MOCKING ---
# On crée de "faux" modules pour que Python ne plante pas lors de l'import
# car ces librairies ne sont pas forcément installées sur ton PC de dev.
sys.modules["cv2"] = MagicMock()
sys.modules["tflite_runtime"] = MagicMock()
sys.modules["tflite_runtime.interpreter"] = MagicMock()
sys.modules["paho"] = MagicMock()
sys.modules["paho.mqtt"] = MagicMock()
sys.modules["paho.mqtt.client"] = MagicMock()

# On importe la fonction APRÈS avoir mocké les modules
from detect_caisse import get_action_decision

class TestLogiqueRobot(unittest.TestCase):

    # --- TESTS LOGIQUE DE BASE (CONFIANCE & TEMPS) ---

    def test_confiance_trop_basse(self):
        # Cas: Caisse noire mais confiance à 80%
        # Le seuil est à > 0.90
        agir, msg = get_action_decision("Caisse noire", 0.80, 0, 100)
        self.assertFalse(agir)
        self.assertIsNone(msg)

    def test_limite_confiance_exacte(self):
        # Cas limite: Exactement 0.90 -> Doit être rejeté (car souvent if conf <= 0.90)
        agir, msg = get_action_decision("Caisse noire", 0.90, 0, 100)
        self.assertFalse(agir, "90% pile ne devrait pas suffire, il faut > 90%")

    def test_limite_confiance_passe(self):
        # Cas limite: 0.91 -> Doit passer
        agir, msg = get_action_decision("Caisse noire", 0.91, 0, 100)
        self.assertTrue(agir, "91% doit passer")

    def test_cooldown_actif(self):
        # Cas: Caisse valide, mais dernière action il y a 1sec (Cooldown = 5s)
        last_time = 100
        current_time = 101
        agir, msg = get_action_decision("Caisse noire", 0.99, last_time, current_time)
        self.assertFalse(agir, "Le robot ne doit pas agir pendant le cooldown")

    def test_limite_cooldown_exact(self):
        # Cas limite: Exactement 5 secondes passées
        # Si last=100 et current=105, diff=5. Si la condition est <= 5, ça bloque.
        last_time = 100
        current_time = 105
        agir, msg = get_action_decision("Caisse noire", 0.99, last_time, current_time)
        self.assertFalse(agir, "A exactement 5s, on devrait être encore dans le cooldown (<=)")

    def test_limite_cooldown_fini(self):
        # Cas limite: 5.1 secondes passées -> OK
        last_time = 100
        current_time = 105.1
        agir, msg = get_action_decision("Caisse noire", 0.99, last_time, current_time)
        self.assertTrue(agir, "Après 5.1s, le cooldown est fini")

    # --- TESTS RECONNAISSANCE CAISSES ---

    def test_caisse_noire_standard(self):
        agir, msg = get_action_decision("Une Caisse Noire", 0.95, 0, 100)
        self.assertTrue(agir)
        self.assertEqual(msg, "CAISSE_NOIRE")

    def test_caisse_bleue_standard(self):
        agir, msg = get_action_decision("Caisse Bleue", 0.95, 0, 100)
        self.assertTrue(agir)
        self.assertEqual(msg, "CAISSE_COULEUR")

    def test_caisse_jaune_standard(self):
        agir, msg = get_action_decision("Caisse Jaune", 0.95, 0, 100)
        self.assertTrue(agir)
        self.assertEqual(msg, "CAISSE_COULEUR")

    # --- TESTS RECONNAISSANCE NID (NOUVEAU) ---

    def test_nid_standard(self):
        # Le cas classique
        agir, msg = get_action_decision("Un Nid", 0.95, 0, 100)
        self.assertTrue(agir)
        self.assertEqual(msg, "ACTION_NID")

    def test_nid_minuscule(self):
        # Vérifie que "nid" fonctionne aussi bien que "Nid"
        agir, msg = get_action_decision("le nid des oiseaux", 0.95, 0, 100)
        self.assertTrue(agir)
        self.assertEqual(msg, "ACTION_NID")

    def test_nid_partiel(self):
        # Vérifie si le mot est collé ou dans une phrase complexe
        agir, msg = get_action_decision("Nid_De_Robot", 0.95, 0, 100)
        self.assertTrue(agir)
        self.assertEqual(msg, "ACTION_NID")

    # --- TESTS DES CHOSES A IGNORER ---

    def test_route_ignoree(self):
        # Cas: Route (confiance 99%) -> Pas d'action
        agir, msg = get_action_decision("Route", 0.99, 0, 100)
        self.assertFalse(agir)

    def test_objet_inconnu(self):
        # Cas: Un truc qui n'est pas dans nos IF
        agir, msg = get_action_decision("Extraterrestre", 0.99, 0, 100)
        self.assertFalse(agir)

    def test_label_vide(self):
        # Cas robuste: chaîne vide
        agir, msg = get_action_decision("", 0.99, 0, 100)
        self.assertFalse(agir)

if __name__ == '__main__':
    unittest.main()