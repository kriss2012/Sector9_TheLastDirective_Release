import os
import sys
import unittest
import pygame

os.environ['SDL_VIDEODRIVER'] = 'dummy'
pygame.init()

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.player import Player
from src.quest_system import QuestManager
from src.save_system import SaveSystem
from src.config import SAVES_DIR

class TestSaveLoad(unittest.TestCase):
    def setUp(self):
        self.player = Player(4.5, 3.2, 1.57)
        self.player.add_item("Science Director's Badge")
        self.player.add_item("Maintenance Tool")
        self.player.add_log("ch1_power_note", "Power Note")
        self.player.health = 85.0

        self.quest_mgr = QuestManager()
        self.quest_mgr.current_chapter = 2
        self.quest_mgr.set_flag("power_restored")

    def test_save_and_load_roundtrip(self):
        test_slot = "test_slot_unit"
        save_res = SaveSystem.save_game(test_slot, self.player, self.quest_mgr, [["#", "."]])
        self.assertTrue(save_res)

        # Create new blank player and quest manager to restore into
        new_player = Player()
        new_quest_mgr = QuestManager()

        loaded_state = SaveSystem.load_game(test_slot, new_player, new_quest_mgr)
        self.assertIsNotNone(loaded_state)
        self.assertEqual(new_quest_mgr.current_chapter, 2)
        self.assertTrue(new_quest_mgr.has_flag("power_restored"))
        self.assertAlmostEqual(new_player.x, 4.5, places=2)
        self.assertAlmostEqual(new_player.y, 3.2, places=2)
        self.assertEqual(new_player.health, 85.0)
        self.assertTrue(new_player.has_item("Science Director's Badge"))
        self.assertTrue(new_player.has_item("Maintenance Tool"))
        self.assertIn("ch1_power_note", new_player.discovered_logs)

        # Cleanup test save
        test_fp = os.path.join(SAVES_DIR, f"{test_slot}.json")
        if os.path.exists(test_fp):
            os.remove(test_fp)

    def test_load_nonexistent_slot(self):
        res = SaveSystem.load_game("non_existent_slot_xyz", self.player, self.quest_mgr)
        self.assertIsNone(res)

if __name__ == "__main__":
    unittest.main()
