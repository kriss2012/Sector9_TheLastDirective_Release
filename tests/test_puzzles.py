import os
import sys
import unittest
import pygame

# Set dummy video driver for headless testing
os.environ['SDL_VIDEODRIVER'] = 'dummy'
pygame.init()

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.puzzles import (
    PowerRoutingPuzzle, MedicalKeypadPuzzle, BiohazardValvesPuzzle,
    DefenseMatrixPuzzle, TransceiverAlignmentPuzzle, SeraHarmonicPuzzle,
    PrimeDirectivePuzzle
)

class TestPuzzles(unittest.TestCase):
    def test_puzzle_1_power_routing(self):
        p = PowerRoutingPuzzle()
        self.assertFalse(p.is_completed)

        # Trigger wrong order or weapon system
        p.switches[3]["state"] = True  # Weapons on
        p._check_solution()
        self.assertFalse(p.is_completed)
        p.switches[3]["state"] = False

        # Correct sequential order: battery -> regulator -> pressure
        p.activation_order = ["battery", "regulator", "pressure"]
        p.switches[0]["state"] = True
        p.switches[1]["state"] = True
        p.switches[2]["state"] = True
        p._check_solution()
        self.assertTrue(p.is_completed)

    def test_puzzle_2_medical_keypad(self):
        p = MedicalKeypadPuzzle()
        self.assertFalse(p.is_completed)

        # Wrong code
        p.entered_code = "123"
        p._check_code()
        self.assertFalse(p.is_completed)

        # Correct code derived from admission timestamps (03:15, 07:40, 11:05 -> 505)
        p.entered_code = "505"
        p._check_code()
        self.assertTrue(p.is_completed)

    def test_puzzle_3_biohazard_valves(self):
        p = BiohazardValvesPuzzle()
        self.assertFalse(p.is_completed)

        # Wrong sequence
        p.closed_valves = ["circle", "helix", "flame"]
        p._check_sequence()
        self.assertFalse(p.is_completed)

        # Correct sequence: Helix -> Circle -> Flame
        p.closed_valves = ["helix", "circle", "flame"]
        p._check_sequence()
        self.assertTrue(p.is_completed)
        self.assertEqual(p.pressure_psi, 0)

    def test_puzzle_4_defense_matrix(self):
        p = DefenseMatrixPuzzle()
        self.assertFalse(p.is_completed)

        # Set correct options: Layer 1=1 (VOSS-9442), Layer 2=1 (WARD-HALT-09), Layer 3=1 (ISOLATE_CORE)
        p.layers[0]["selected"] = 1
        p.layers[1]["selected"] = 1
        p.layers[2]["selected"] = 1
        p._check_all()
        self.assertTrue(p.is_completed)

    def test_puzzle_5_transceiver_alignment(self):
        p = TransceiverAlignmentPuzzle()
        self.assertFalse(p.is_completed)

        # Set exact telemetry targets
        p.dishes[0]["azimuth"] = 45
        p.dishes[0]["elevation"] = 12
        p.dishes[1]["azimuth"] = 180
        p.dishes[1]["elevation"] = -5
        p.dishes[2]["azimuth"] = 290
        p.dishes[2]["elevation"] = 33
        p._check_signal()
        self.assertTrue(p.is_completed)

    def test_puzzle_6_sera_harmonics(self):
        p = SeraHarmonicPuzzle()
        self.assertFalse(p.is_completed)

        # Tune exact frequencies: 420, 840, 1260
        p.frequencies[0]["freq"] = 420
        p.frequencies[1]["freq"] = 840
        p.frequencies[2]["freq"] = 1260
        p._check_resonance()
        self.assertTrue(p.is_completed)

    def test_puzzle_7_prime_directive(self):
        # Standard directives
        p = PrimeDirectivePuzzle(secret_unlocked=False)
        self.assertEqual(len(p.options), 3)

        # Secret directive unlocked
        p_sec = PrimeDirectivePuzzle(secret_unlocked=True)
        self.assertEqual(len(p_sec.options), 4)
        self.assertEqual(p_sec.options[3]["code"], "S")

if __name__ == "__main__":
    unittest.main()
