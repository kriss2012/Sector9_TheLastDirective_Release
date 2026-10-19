import os
import sys
import unittest
import pygame

os.environ['SDL_VIDEODRIVER'] = 'dummy'
pygame.init()

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.cinematics import CinematicsManager
from src.quest_system import QuestManager
from src.player import Player

class TestEndings(unittest.TestCase):
    def setUp(self):
        self.cinematics = CinematicsManager()
        self.quest_mgr = QuestManager()
        self.player = Player()

    def test_all_four_endings_data_valid(self):
        for code in ["A", "B", "C", "S"]:
            data = self.cinematics.get_ending_data(code)
            self.assertIn("title", data)
            self.assertIn("cinematic_lines", data)
            self.assertIn("epilogue", data)
            self.assertTrue(len(data["cinematic_lines"]) > 0)
            self.assertTrue(len(data["epilogue"]) > 0)

    def test_ending_prerequisites(self):
        # Ending A, B, C are always available in Chapter 6
        # Secret ending requires Dr. Sera Sync and 3 Veyr Fragments
        self.assertFalse(self.quest_mgr.can_access_secret_ending(self.player))

        self.player.add_log("veyr_fragment_1", "Frag 1")
        self.player.add_log("veyr_fragment_2", "Frag 2")
        self.player.add_log("veyr_fragment_3", "Frag 3")
        self.quest_mgr.set_flag("sera_synced")

        self.assertTrue(self.quest_mgr.can_access_secret_ending(self.player))

if __name__ == "__main__":
    unittest.main()
