import json
import os
import time
from src.config import SAVES_DIR

class SaveSystem:
    SAVE_VERSION = "1.0.0"

    @classmethod
    def save_game(cls, slot_name, player, quest_manager, level_map, extra_state=None):
        os.makedirs(SAVES_DIR, exist_ok=True)
        file_path = os.path.join(SAVES_DIR, f"{slot_name}.json")

        state = {
            "version": cls.SAVE_VERSION,
            "timestamp": time.time(),
            "date_str": time.strftime("%Y-%m-%d %H:%M:%S"),
            "chapter": quest_manager.current_chapter,
            "completed_chapters": quest_manager.completed_chapters,
            "story_flags": list(quest_manager.story_flags),
            "objectives_state": quest_manager.get_objectives(),
            "player": {
                "x": player.x,
                "y": player.y,
                "angle": player.angle,
                "health": player.health,
                "flashlight_battery": player.flashlight_battery,
                "inventory": player.inventory,
                "journal": player.journal,
                "discovered_logs": list(player.discovered_logs)
            },
            "level_map": level_map,
            "extra_state": extra_state or {}
        }

        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(state, f, indent=4)
            return True
        except Exception as e:
            print(f"[SaveSystem] Error saving to {file_path}: {e}")
            return False

    @classmethod
    def load_game(cls, slot_name, player, quest_manager):
        file_path = os.path.join(SAVES_DIR, f"{slot_name}.json")
        if not os.path.exists(file_path):
            return None

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                state = json.load(f)

            quest_manager.current_chapter = state.get("chapter", 0)
            quest_manager.completed_chapters = state.get("completed_chapters", [])
            quest_manager.story_flags = set(state.get("story_flags", []))

            # Restore objectives state
            saved_objs = state.get("objectives_state", [])
            curr_objs = quest_manager.get_objectives()
            saved_dict = {o["id"]: o.get("completed", False) for o in saved_objs}
            for obj in curr_objs:
                if obj["id"] in saved_dict:
                    obj["completed"] = saved_dict[obj["id"]]

            p_data = state.get("player", {})
            player.x = p_data.get("x", player.x)
            player.y = p_data.get("y", player.y)
            player.angle = p_data.get("angle", player.angle)
            player.health = p_data.get("health", 100.0)
            player.flashlight_battery = p_data.get("flashlight_battery", 100.0)
            player.inventory = p_data.get("inventory", [])
            player.journal = p_data.get("journal", [])
            player.discovered_logs = set(p_data.get("discovered_logs", []))

            level_map = state.get("level_map")
            return state
        except Exception as e:
            print(f"[SaveSystem] Error loading from {file_path}: {e}")
            return None

    @classmethod
    def list_save_slots(cls):
        os.makedirs(SAVES_DIR, exist_ok=True)
        slots = []
        for fn in os.listdir(SAVES_DIR):
            if fn.endswith(".json"):
                name = fn[:-5]
                fp = os.path.join(SAVES_DIR, fn)
                try:
                    with open(fp, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    slots.append({
                        "name": name,
                        "chapter": data.get("chapter", 0),
                        "date_str": data.get("date_str", "Unknown")
                    })
                except:
                    slots.append({"name": name, "chapter": 0, "date_str": "Corrupt"})
        return slots
