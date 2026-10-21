"""Tests for the space-lobby door/lock system and mission chain.

These tests are pure Python (no pygame) so they also run on a bare CI box.
"""
import json
import os
import re
import sys
import unittest
from collections import deque

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.door_system import Door, DoorSystem, LOCK_KEY, LOCK_FLAG, LOCK_NONE
from src import lobby_layout as L
from src.lobby_logic import LobbyLogic


class FakeState:
    def __init__(self):
        self.items, self.flags, self.done, self.logs, self.msgs, self.sounds = [], set(), set(), {}, [], []

    def has_item(self, n): return n in self.items
    def add_item(self, n):
        if n in self.items: return False
        self.items.append(n); return True
    def remove_item(self, n): self.items.remove(n)
    def has_flag(self, f): return f in self.flags
    def set_flag(self, f): self.flags.add(f)
    def complete(self, o): self.done.add(o)
    def add_log(self, k, t): self.logs[k] = t
    def say(self, m): self.msgs.append(m)
    def play(self, s): self.sounds.append(s)


def tick(logic, seconds, pos=(1.5, 5.5), step=0.05):
    for _ in range(int(seconds / step)):
        logic.update(step, pos)


class TestDoor(unittest.TestCase):
    def test_open_close_cycle(self):
        d = Door("a", (3, 3), "A", LOCK_NONE, auto_close=1.0, speed=2.0)
        self.assertEqual(d.state, "closed")
        self.assertTrue(d.solid)
        d.open()
        for _ in range(12):
            d.update(0.05)
        self.assertEqual(d.state, "open")
        self.assertFalse(d.solid)
        for _ in range(60):
            d.update(0.05)
        self.assertEqual(d.state, "closed")
        self.assertEqual(d.progress, 0.0)

    def test_never_crushes_player(self):
        d = Door("a", (3, 3), "A", LOCK_NONE, auto_close=0.2, speed=2.0)
        d.open()
        for _ in range(100):
            d.update(0.05, blocked=True)
        self.assertEqual(d.state, "open")          # held open while occupied
        self.assertEqual(d.progress, 1.0)
        for _ in range(100):
            d.update(0.05, blocked=False)
        self.assertEqual(d.state, "closed")

    def test_key_lock(self):
        d = Door("k", (3, 3), "K", LOCK_KEY, requires="Card")
        self.assertTrue(d.is_locked)
        self.assertFalse(d.check_access(lambda n: False, lambda f: False)[0])
        self.assertTrue(d.check_access(lambda n: n == "Card", lambda f: False)[0])

    def test_lock_closes_open_door_first(self):
        d = Door("a", (3, 3), "A", LOCK_NONE, auto_close=None, speed=4.0)
        d.open()
        for _ in range(20):
            d.update(0.05)
        self.assertEqual(d.state, "open")
        d.lock()
        for _ in range(40):
            d.update(0.05)
        self.assertEqual(d.state, "locked")

    def test_grid_sync_marks_open_doors_passable(self):
        ds = DoorSystem([Door("a", (1, 1), "A", LOCK_NONE, speed=4.0)])
        grid = [list("###"), list("#D#"), list("###")]
        ds.sync_grid(grid)
        self.assertEqual(grid[1][1], 'D')
        ds.get("a").open()
        for _ in range(20):
            ds.update(0.05)
        ds.sync_grid(grid)
        self.assertEqual(grid[1][1], 'O')


class TestLayout(unittest.TestCase):
    def setUp(self):
        self.grid = L.build_grid()

    def test_dimensions(self):
        self.assertEqual(len(self.grid), L.HEIGHT)
        for row in self.grid:
            self.assertEqual(len(row), L.WIDTH)

    def test_spawn_is_open_floor(self):
        x, y, _ = L.SPAWN
        self.assertEqual(self.grid[int(y)][int(x)], '.')

    def test_every_door_cell_is_D_and_framed_by_walls(self):
        for cell, did in L.DOOR_CELLS.items():
            x, y = cell
            self.assertEqual(self.grid[y][x], 'D', did)
            if did == "launch":                      # east wall door, vertical
                self.assertEqual(self.grid[y - 1][x], '#')
                self.assertEqual(self.grid[y + 1][x], '#')
            else:                                    # horizontal wall door
                self.assertIn(self.grid[y][x - 1], '#Z')
                self.assertIn(self.grid[y][x + 1], '#Z')

    def test_doors_match_door_system(self):
        ds = L.build_doors()
        self.assertEqual({d.cell for d in ds.doors.values()}, set(L.DOOR_CELLS))

    def test_everything_reachable_with_doors_open(self):
        h, w = len(self.grid), len(self.grid[0])
        sx, sy = int(L.SPAWN[0]), int(L.SPAWN[1])
        seen, q = {(sx, sy)}, deque([(sx, sy)])
        while q:
            x, y = q.popleft()
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                nx, ny = x + dx, y + dy
                if 0 <= nx < w and 0 <= ny < h and (nx, ny) not in seen and self.grid[ny][nx] in '.D':
                    seen.add((nx, ny)); q.append((nx, ny))
        floors = {(x, y) for y in range(h) for x in range(w) if self.grid[y][x] in '.D'}
        self.assertEqual(floors - seen, set())

    def test_rooms_unreachable_while_doors_closed(self):
        # With every door solid, only the corridor is reachable from spawn.
        h, w = len(self.grid), len(self.grid[0])
        sx, sy = int(L.SPAWN[0]), int(L.SPAWN[1])
        seen, q = {(sx, sy)}, deque([(sx, sy)])
        while q:
            x, y = q.popleft()
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                nx, ny = x + dx, y + dy
                if 0 <= nx < w and 0 <= ny < h and (nx, ny) not in seen and self.grid[ny][nx] == '.':
                    seen.add((nx, ny)); q.append((nx, ny))
        self.assertTrue(all(y in L.CORRIDOR_Y for _, y in seen))

    def test_interactions_do_not_overlap_within_reach(self):
        """handle_interactions scans a 3x3 around the player: no two interactables
        may share one, or the wrong prompt could win."""
        cells = list(L.build_interactions())
        for i, a in enumerate(cells):
            for b in cells[i + 1:]:
                self.assertTrue(abs(a[0] - b[0]) > 2 or abs(a[1] - b[1]) > 2, (a, b))

    def test_sprites_inside_floor_and_clear_of_door_reach(self):
        for eid, _, x, y, _, _ in L.SPRITES:
            self.assertEqual(self.grid[int(y)][int(x)], '.', eid)
            for dcell in L.DOOR_CELLS:
                self.assertTrue(abs(int(x) - dcell[0]) > 1 or abs(int(y) - dcell[1]) > 1, (eid, dcell))

    def test_wall_styles_cover_all_walls(self):
        m = L.build_wall_tex_map(self.grid)
        self.assertTrue(all(v in (L.STYLE_ORANGE, L.STYLE_SILVER, L.STYLE_WHITE) for v in m.values()))
        self.assertEqual(len(m), sum(r.count('#') for r in self.grid))


class TestMissionPlaythrough(unittest.TestCase):
    def setUp(self):
        self.s = FakeState()
        self.doors = L.build_doors()
        self.logic = LobbyLogic(self.s, self.doors)

    def open_door(self, did):
        self.logic.interact_door(did)
        tick(self.logic, 1.5)
        return self.doors.get(did)

    def test_full_mission_chain(self):
        lg, s, ds = self.logic, self.s, self.doors

        # 0. Compass starts at the supply locker; mission control is locked.
        self.assertIn("SUPPLY", lg.objective_target()[2])
        lg.interact_door("mission_control")
        self.assertTrue(ds.get("mission_control").is_locked)
        self.assertIn("REQUIRES", s.msgs[-1])

        # 1. Supply locker opens freely -> keycard 1
        self.assertFalse(self.open_door("supply").solid)
        self.assertTrue(lg.pickup("lobby_keycard1"))
        self.assertIn("get_keycard1", s.done)

        # 2. Mission control opens with the keycard; accept mission, learn code
        self.assertFalse(self.open_door("mission_control").solid)
        lg.interact_terminal("mission_board")
        self.assertIn(L.FLAG_ACCEPTED, s.flags)
        self.assertIn(L.ANNEX_CODE, s.msgs[-1])
        self.assertIn("lobby_briefing", s.logs)

        # 3. Annex is a keypad door: interaction returns the keypad action
        act = lg.interact_door("annex")
        self.assertEqual(act["action"], "keypad")
        self.assertEqual(act["code"], "7319")
        self.assertTrue(ds.get("annex").is_locked)
        lg.keypad_success("annex")
        tick(lg, 1.5)
        self.assertFalse(ds.get("annex").solid)
        self.assertIn("crack_annex_code", s.done)
        lg.pickup("lobby_power_cell")

        # 4. Airlock bay has no power yet
        lg.interact_door("airlock_bay")
        self.assertTrue(ds.get("airlock_bay").is_locked)
        self.assertIn("NO POWER", s.msgs[-1])
        lg.interact_terminal("power_node")
        self.assertIn(L.FLAG_POWER, s.flags)
        self.assertNotIn(L.ITEM_CELL, s.items)           # cell consumed
        self.assertFalse(ds.get("airlock_bay").is_locked)  # power unlocked it
        self.assertFalse(self.open_door("airlock_bay").solid)
        lg.pickup("lobby_keycard2")

        # 5. Hangar needs keycard 2
        self.assertFalse(self.open_door("hangar").solid)
        self.assertIn("open_hangar", s.done)

        # 6. Data chip triggers lockdown: every door seals, launch stays sealed
        self.assertTrue(lg.pickup("lobby_datachip"))
        self.assertTrue(ds.lockdown_active)
        tick(lg, 4.0)
        for d in ds.doors.values():
            self.assertTrue(d.is_locked, d.id)
        lg.interact_door("hangar")
        self.assertIn("LOCKDOWN", s.msgs[-1])
        lg.interact_door("launch")
        self.assertTrue(ds.get("launch").is_locked)
        self.assertFalse(lg.launch_requested)

        # 7. Lockdown ends: earned unlocks are restored, launch comes online
        tick(lg, L.LOCKDOWN_SECONDS)
        self.assertFalse(ds.lockdown_active)
        self.assertIn(L.FLAG_LAUNCH_READY, s.flags)
        self.assertIn("survive_lockdown", s.done)
        self.assertFalse(ds.get("hangar").is_locked)       # keycard door restored
        self.assertFalse(ds.get("annex").is_locked)        # keypad door stays solved
        self.assertFalse(ds.get("mission_control").is_locked)

        # 8. Launch
        act = lg.interact_door("launch")
        self.assertEqual(act, {"action": "launch"})
        self.assertTrue(lg.launch_requested)

    def test_lockdown_never_traps_player_in_doorway(self):
        lg, ds = self.logic, self.doors
        lg.interact_door("supply")
        tick(lg, 1.5)
        door_center = (2.5, 3.5)
        lg.pickup("lobby_datachip")                   # lockdown starts while door is open
        tick(lg, 6.0, pos=door_center)                # player stands in the doorway
        self.assertFalse(ds.get("supply").solid)      # door held open
        tick(lg, 2.0, pos=(2.5, 5.5))                 # player steps away
        self.assertTrue(ds.get("supply").solid)

    def test_prompts(self):
        lg = self.logic
        p = lg.prompt({"type": "lobby_door", "id": "annex"})
        self.assertIn("Keypad", p)
        p = lg.prompt({"type": "lobby_door", "id": "mission_control"})
        self.assertIn("NEEDS Level-1 Keycard", p)
        p = lg.prompt({"type": "lobby_door", "id": "airlock_bay"})
        self.assertTrue(p.endswith("LOCKED"))
        # every possible prompt must fit the HUD's 420px box (~45 chars)
        for did in L.DOOR_CELLS.values():
            self.assertLessEqual(len(lg.prompt({"type": "lobby_door", "id": did})), 46, did)
        p = lg.prompt({"type": "lobby_door", "id": "supply"})
        self.assertTrue(p.startswith("[E] Open"))
        self.assertIn("OFFLINE", lg.prompt({"type": "lobby_terminal", "id": "power_node"}))

    def test_wrong_order_cannot_skip_chain(self):
        lg, s = self.logic, self.s
        lg.interact_terminal("power_node")               # no cell
        self.assertNotIn(L.FLAG_POWER, s.flags)
        lg.interact_door("launch")
        self.assertFalse(lg.launch_requested)
        lg.interact_door("hangar")
        self.assertTrue(self.doors.get("hangar").is_locked)

    def test_resume_from_save_unlocked_doors_and_chip(self):
        s = FakeState()
        s.flags |= {"door_unlocked:mission_control", L.FLAG_CHIP}
        doors = L.build_doors(unlocked_ids=("mission_control",))
        LobbyLogic(s, doors)
        self.assertFalse(doors.get("mission_control").is_locked)
        self.assertIn(L.FLAG_LAUNCH_READY, s.flags)      # no softlock after loading


DATA = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets", "data")


class TestDataConsistency(unittest.TestCase):
    """The pure-Python rules and the JSON data files must agree."""

    def test_every_objective_the_logic_completes_exists_in_chapters_json(self):
        chapters = json.load(open(os.path.join(DATA, "chapters.json"), encoding="utf-8"))
        ids = {o["id"] for o in chapters["7"]["objectives"]}
        src = open(os.path.join(os.path.dirname(DATA), "..", "src", "lobby_logic.py"), encoding="utf-8").read()
        used = set(re.findall(r'complete\("([a-z0-9_]+)"\)', src))
        used |= {v for v in __import__("src.lobby_logic", fromlist=["x"]).DOOR_OBJECTIVES.values()}
        used.add("launch")   # completed by the engine on launch
        self.assertEqual(used - ids, set())

    def test_journal_logs_exist_and_briefing_matches_keypad_code(self):
        from src.lobby_logic import LOG_TITLES
        lore = json.load(open(os.path.join(DATA, "lore_logs.json"), encoding="utf-8"))
        for key, title in LOG_TITLES.items():
            self.assertIn(key, lore)
            self.assertEqual(lore[key]["title"], title)
        self.assertIn(L.ANNEX_CODE, lore["lobby_briefing"]["content"])

    def test_chapters_json_has_lobby_deck_name(self):
        chapters = json.load(open(os.path.join(DATA, "chapters.json"), encoding="utf-8"))
        self.assertEqual(chapters["7"]["theme"], "lobby")
        self.assertTrue(chapters["7"]["deck"])


if __name__ == "__main__":
    unittest.main()
