import json
import os
from src.config import DATA_DIR
from src.sound_system import SoundSystem

class QuestManager:
    def __init__(self):
        self.chapters_data = {}
        self.load_data()
        self.current_chapter = 0
        self.story_flags = set()
        self.completed_chapters = []
        self.ending_selected = None
        self.sound = SoundSystem.get_instance()

    def load_data(self):
        path = os.path.join(DATA_DIR, "chapters.json")
        if os.path.exists(path):
            with open(path, 'r', encoding='utf-8') as f:
                self.chapters_data = json.load(f)

    def get_current_chapter_info(self):
        return self.chapters_data.get(str(self.current_chapter), {})

    def get_objectives(self):
        info = self.get_current_chapter_info()
        return info.get("objectives", [])

    def get_main_objective(self):
        info = self.get_current_chapter_info()
        return info.get("main_objective", "Explore the warship and follow mission directives.")

    def set_flag(self, flag_name):
        self.story_flags.add(flag_name)

    def has_flag(self, flag_name):
        return flag_name in self.story_flags

    def complete_objective(self, obj_id, player=None):
        info = self.get_current_chapter_info()
        objectives = info.get("objectives", [])
        for obj in objectives:
            if obj["id"] == obj_id and not obj["completed"]:
                obj["completed"] = True
                if player:
                    player.journal.append(f"Completed: {obj['text']}")
                self.sound.play('access_granted')
                return True
        return False

    def is_chapter_complete(self):
        info = self.get_current_chapter_info()
        objectives = info.get("objectives", [])
        required_objs = [o for o in objectives if o.get("required", True)]
        return all(o.get("completed", False) for o in required_objs)

    def advance_chapter(self, player=None):
        if self.current_chapter not in self.completed_chapters:
            self.completed_chapters.append(self.current_chapter)
        if self.current_chapter < 6:
            self.current_chapter += 1
            if player:
                info = self.get_current_chapter_info()
                player.journal.append(f"Chapter {self.current_chapter} Commenced: {info.get('title', '')}")
            return True
        return False

    def can_access_secret_ending(self, player):
        # Requires all 3 Veyr fragments discovered and Dr. Sera harmonic sync solved
        has_fragments = (
            "veyr_fragment_1" in player.discovered_logs and
            "veyr_fragment_2" in player.discovered_logs and
            "veyr_fragment_3" in player.discovered_logs
        )
        has_sera_sync = self.has_flag("sera_synced")
        return has_fragments and has_sera_sync
