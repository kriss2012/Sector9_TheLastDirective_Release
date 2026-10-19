import os
import sys
import unittest
import pygame

os.environ['SDL_VIDEODRIVER'] = 'dummy'
pygame.init()

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.player import Player
from src.quest_system import QuestManager
from src.levels import LevelManager

class TestQuests(unittest.TestCase):
    def setUp(self):
        self.quest_mgr = QuestManager()
        self.player = Player()

    def test_chapter_progression(self):
        # Prologue (Chapter 0)
        self.assertEqual(self.quest_mgr.current_chapter, 0)
        objs = self.quest_mgr.get_objectives()
        self.assertTrue(len(objs) > 0)

        # Complete required objectives
        for o in objs:
            if o.get("required", True):
                self.quest_mgr.complete_objective(o["id"], self.player)

        self.assertTrue(self.quest_mgr.is_chapter_complete())
        res = self.quest_mgr.advance_chapter(self.player)
        self.assertTrue(res)
        self.assertEqual(self.quest_mgr.current_chapter, 1)

    def test_all_seven_chapters_loadable(self):
        for ch_id in range(7):
            level = LevelManager.get_level(ch_id)
            self.assertEqual(level.chapter_id, ch_id)
            self.assertTrue(len(level.map_grid) > 0)
            self.assertTrue(len(level.map_grid[0]) > 0)
            # Check player spawn is inside bounds
            sp_x, sp_y, _ = level.player_spawn
            self.assertTrue(0 <= int(sp_x) < len(level.map_grid[0]))
            self.assertTrue(0 <= int(sp_y) < len(level.map_grid))

    def test_secret_ending_conditions(self):
        # Initial: should not be able to access secret ending
        self.assertFalse(self.quest_mgr.can_access_secret_ending(self.player))

        # Add fragments
        self.player.add_log("veyr_fragment_1", "Frag 1")
        self.player.add_log("veyr_fragment_2", "Frag 2")
        self.player.add_log("veyr_fragment_3", "Frag 3")
        self.assertFalse(self.quest_mgr.can_access_secret_ending(self.player))

        # Set sera sync flag
        self.quest_mgr.set_flag("sera_synced")
        self.assertTrue(self.quest_mgr.can_access_secret_ending(self.player))

if __name__ == "__main__":
    unittest.main()
