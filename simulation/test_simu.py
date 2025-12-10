import unittest
from unittest.mock import patch
import robot
import map_points
import main
from menu import RobotConfig


class TestEurobotComplete(unittest.TestCase):

    def setUp(self):
        """S'exécute AVANT chaque test : On remet tout à zéro."""
        self.bot = robot.Robot(x=0, y=0, theta=0, color="blue", speed=1000)
        self.zones = map_points.generer_graphe()
        self.config = RobotConfig("blue")

    # TESTS ZONES
    def test_01_creation_zones(self):
        """Vérifie qu'on a bien généré des zones."""
        self.assertGreater(len(self.zones), 0)
        # On vérifie qu'on a bien les 3 types
        types = [z.type for z in self.zones]
        self.assertIn('nid', types)
        self.assertIn('gm', types)
        self.assertIn('ramassage', types)

    def test_02_capacite_gm(self):
        """Vérifie qu'un Garde-Manger est limité à 4 caisses."""
        gm = next(z for z in self.zones if z.type == 'gm')
        self.assertEqual(gm.max_caisses, 4)

    def test_03_capacite_nid(self):
        """Vérifie que le Nid a une grosse capacité (50)."""
        nid = next(z for z in self.zones if z.type == 'nid')
        self.assertEqual(nid.max_caisses, 50)

    def test_04_position_zone(self):
        """Vérifie le calcul du centre d'une zone."""
        # On crée une zone fictive en (0,0) de taille 100x100
        z = map_points.Zone(0, 0, "Test")
        z.largeur = 100
        z.profondeur = 100
        self.assertEqual(z.centre, (50, 50))

    def test_05_ramassage_initial(self):
        """Vérifie que les zones de ramassage commencent avec 4 caisses."""
        ramasse = next(z for z in self.zones if z.type == 'ramassage')
        self.assertEqual(ramasse.nb_caisses, 4)

    # TEST MOUVEMENT ROBOT
    def test_06_calcul_distance(self):
        """Vérifie que le robot sait calculer quand il est arrivé."""
        # Distance < 10 = Arrivé
        self.bot.x, self.bot.y = 100, 100
        arrived = self.bot.move_to(105, 100, dt=1) # à 5 pixels
        self.assertTrue(arrived, "Le robot devrait considérer qu'il est arrivé")

    def test_07_mouvement_lineaire(self):
        """Vérifie que le robot avance vers la cible."""
        self.bot.x, self.bot.y = 0, 0
        target_x, target_y = 1000, 0
        dt = 0.1  # 0.1 seconde

        # Le robot regarde vers 0 (droite), il doit avancer en X
        self.bot.move_to(target_x, target_y, dt)

        expected_x = self.bot.base_speed * dt  # 1000 * 0.1 = 100
        self.assertAlmostEqual(self.bot.x, expected_x, delta=1.0)
        self.assertEqual(self.bot.y, 0)  # Ne doit pas bouger en Y

    def test_08_rotation_automatique(self):
        """Vérifie que le robot tourne vers sa cible."""
        self.bot.x, self.bot.y = 0, 0
        self.bot.theta = 0
        # Cible en haut (90 degrés)
        self.bot.move_to(0, 100, dt=0.1)
        self.assertAlmostEqual(self.bot.theta, 90, delta=1.0)

    def test_09_vitesse_max(self):
        """Vérifie que le robot ne dépasse pas la cible en un pas."""
        self.bot.x, self.bot.y = 0, 0
        # Cible très proche (20px) mais vitesse énorme (1000px/s)
        self.bot.move_to(20, 0, dt=1.0)

        # Il doit s'arrêter à 20, pas aller à 1000
        self.assertLessEqual(self.bot.x, 25) # Marge d'erreur de la condition d'arrêt

    @patch('random.uniform')
    def test_10_bruit_vitesse(self, mock_random):
        """Vérifie que le bruit est appliqué à la vitesse."""
        mock_random.return_value = -50 # On force le bruit à -50
        self.bot.base_speed = 500
        self.bot.speed_noise = 50

        self.bot.move_to(1000, 0, dt=1)

        # Vitesse effective = 500 - 50 = 450
        expected_x = 450
        self.assertAlmostEqual(self.bot.x, expected_x, delta=1.0)

    # TEST STRATEGIE ROBOT

    def test_11_trouver_pickup_le_plus_proche(self):
        """Le robot doit choisir la zone de ramassage la plus proche."""
        self.bot.x, self.bot.y = 0, 0

        # On simule 2 zones : une proche, une loin
        z_proche = map_points.Ramassage(100, 0, "Proche")
        z_loin = map_points.Ramassage(2000, 0, "Loin")
        zones_test = [z_proche, z_loin]

        target = self.bot.get_nearest_pickup_with_stock(zones_test)
        self.assertEqual(target, z_proche)

    def test_12_ignorer_pickup_vide(self):
        """Le robot ne doit pas aller vers une zone vide."""
        self.bot.x, self.bot.y = 0, 0
        z_proche_vide = map_points.Ramassage(100, 0, "Proche Vide")
        z_proche_vide.nb_caisses = 0 # VIDE

        z_loin_plein = map_points.Ramassage(2000, 0, "Loin Plein")
        z_loin_plein.nb_caisses = 4

        zones_test = [z_proche_vide, z_loin_plein]

        target = self.bot.get_nearest_pickup_with_stock(zones_test)
        self.assertEqual(target, z_loin_plein)

    @patch('random.uniform')
    def test_13_strategie_risque_gm(self, mock_random):
        """Si le tirage est favorable (< risk), aller au Garde-Manger."""
        mock_random.return_value = 10 # Tirage bas
        risk = 50

        target = self.bot.decide_strategy(self.zones, risk)
        self.assertEqual(target.type, 'gm')

    @patch('random.uniform')
    def test_14_strategie_securite_nid(self, mock_random):
        """Si le tirage est défavorable (> risk), rentrer au Nid."""
        mock_random.return_value = 90 # Tirage haut
        risk = 50

        target = self.bot.decide_strategy(self.zones, risk)
        self.assertEqual(target.type, 'nid')
        self.assertIn("Bleu", target.nom) # Robot bleu -> Nid Bleu

    def test_15_ignorer_gm_plein(self):
        """Le robot ne doit pas choisir un Garde-Manger plein."""
        self.bot.x, self.bot.y = 0, 0

        gm_plein = map_points.GardeManger(10, 10, "GM Plein")
        gm_plein.nb_caisses = 4 # MAX

        gm_vide = map_points.GardeManger(2000, 2000, "GM Vide")
        gm_vide.nb_caisses = 0

        zones_test = [gm_plein, gm_vide]

        # On force la recherche de GM
        target = self.bot.get_nearest_zone(zones_test, 'gm')

        self.assertEqual(target, gm_vide, "Il aurait dû ignorer le GM plein même s'il est proche")

    # TEST SCORE ET ACTIONS
    def test_16_score_base_nid(self):
        """1 caisse au nid = 1 point."""
        nid = next(z for z in self.zones if z.nom == "Nid Bleu")
        nid.nb_caisses = 5

        score, _, _ = main.calculate_score(self.zones, "blue")
        self.assertEqual(score, 5)

    def test_17_score_gm_bonus(self):
        """1 caisse en GM = 3 points."""
        gm = next(z for z in self.zones if z.type == "gm")
        gm.nb_caisses = 2

        score, _, _ = main.calculate_score(self.zones, "blue")
        self.assertEqual(score, 6) # 2 * 3

    def test_18_score_mixte(self):
        """Test combiné Nid + GM."""
        nid = next(z for z in self.zones if z.nom == "Nid Bleu")
        nid.nb_caisses = 2
        gm = next(z for z in self.zones if z.type == "gm")
        gm.nb_caisses = 1

        score, _, _ = main.calculate_score(self.zones, "blue")
        self.assertEqual(score, 5) # (2*1) + (1*3)

    def test_19_duree_action_minimum(self):
        """Une action ne doit pas durer 0s ou être négative."""
        duration = main.calculate_action_duration(base_time=0, noise=0, prob_fail=0, fail_penalty=0)
        self.assertEqual(duration, 0.1) # Valeur minimale forcée dans ton code

    @patch('random.uniform')
    def test_20_echec_action(self, mock_random):
        """Test de la pénalité de temps en cas d'échec."""
        # Premier appel pour le bruit (0), Second appel pour le fail (0 < 50)
        mock_random.side_effect = [0, 10] 

        base = 1.0
        penalty = 5.0
        duration = main.calculate_action_duration(base, 0, 50, penalty)

        self.assertEqual(duration, base + penalty)


if __name__ == '__main__':
    unittest.main()