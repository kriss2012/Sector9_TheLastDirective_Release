"""Lobby mission rules (pure Python, no pygame import).

`state` is any object with this duck-typed interface (the game adapts Player +
QuestManager to it; the unit tests use a tiny fake):

    has_item(name) / add_item(name) / remove_item(name)
    has_flag(name) / set_flag(name)
    complete(objective_id)
    add_log(key, title)
    say(message)           # HUD feedback banner
    play(sound_name)
"""
from src.door_system import LOCK_CODE, LOCK_FLAG, LOCK_KEY
from src.lobby_layout import (
    ANNEX_CODE, LOCKDOWN_SECONDS, ITEM_KEY1, ITEM_KEY2, ITEM_CELL, ITEM_CHIP,
    FLAG_ACCEPTED, FLAG_POWER, FLAG_CHIP, FLAG_LAUNCH_READY,
)

DOOR_OBJECTIVES = {"mission_control": "enter_mission_control", "hangar": "open_hangar"}

LOG_TITLES = {
    "lobby_briefing": "Mission Briefing: Operation Hangar Run",
    "lobby_crew_log": "Crew Quarters Log - Tech Okafor",
    "lobby_obs_log": "Observation Lounge Log - Lt. Adeyemi",
}


class LobbyLogic:
    def __init__(self, state, doors):
        self.state = state
        self.doors = doors
        self._alarm_timer = 0.0
        self.launch_requested = False
        # Reconcile a save made mid-lockdown: the chip is taken, nothing is left to wait for.
        if state.has_flag(FLAG_CHIP) and not state.has_flag(FLAG_LAUNCH_READY):
            state.set_flag(FLAG_LAUNCH_READY)

    # ---------------------------------------------------------------- helpers
    def _unlock(self, door):
        door.unlock()
        self.state.set_flag(f"door_unlocked:{door.id}")

    def _objective_for(self, door_id):
        obj = DOOR_OBJECTIVES.get(door_id)
        if obj:
            self.state.complete(obj)

    # ------------------------------------------------------------------ doors
    def interact_door(self, door_id):
        """Returns None, or an action dict: {'action': 'keypad'|'launch', ...}."""
        s = self.state
        d = self.doors.get(door_id)
        if d is None:
            return None

        if d.is_locked:
            ok, reason = d.check_access(s.has_item, s.has_flag)
            if ok:
                self._unlock(d)
                s.play("access_granted")
                s.say(f"{d.label}: ACCESS GRANTED")
            elif d.lock_type == LOCK_CODE and not d.in_lockdown:
                s.play("ui_beep")
                return {"action": "keypad", "door_id": d.id, "code": d.code, "title": d.label}
            else:
                s.play("access_denied")
                s.say(reason)
                return None

        if d.launch:
            d.open()
            self.launch_requested = True
            return {"action": "launch"}

        if d.state in ("closed", "closing"):
            d.open()
            self._objective_for(d.id)
        elif d.state in ("open", "opening"):
            d.toggle()
        return None

    def keypad_success(self, door_id):
        d = self.doors.get(door_id)
        if d is None:
            return
        self._unlock(d)
        d.open()
        self.state.complete("crack_annex_code")
        self.state.play("access_granted")
        self.state.say(f"{d.label}: KEYPAD ACCEPTED - DOOR UNLOCKED")

    # -------------------------------------------------------------- terminals
    def interact_terminal(self, terminal_id):
        s = self.state
        if terminal_id == "mission_board":
            if not s.has_flag(FLAG_ACCEPTED):
                s.set_flag(FLAG_ACCEPTED)
                s.complete("accept_mission")
                s.add_log("lobby_briefing", LOG_TITLES["lobby_briefing"])
                s.play("access_granted")
                s.say(f"MISSION ACCEPTED - ANNEX OVERRIDE CODE: {ANNEX_CODE}")
            elif not s.has_flag(FLAG_POWER):
                s.play("ui_beep")
                s.say(f"BOARD: ENGINEERING ANNEX CODE {ANNEX_CODE} - POWER CELL REQUIRED FOR AIRLOCK BAY")
            else:
                s.play("ui_beep")
                s.say("BOARD: RETRIEVE MISSION DATA CHIP FROM THE HANGAR, THEN LAUNCH")
        elif terminal_id == "power_node":
            if s.has_flag(FLAG_POWER):
                s.play("ui_beep")
                s.say("AUXILIARY POWER NODE: ONLINE")
            elif s.has_item(ITEM_CELL):
                s.remove_item(ITEM_CELL)
                s.set_flag(FLAG_POWER)
                s.complete("restore_power")
                for d in self.doors.doors.values():
                    if d.lock_type == LOCK_FLAG and d.requires == FLAG_POWER:
                        self._unlock(d)
                s.play("access_granted")
                s.say("POWER CELL INSTALLED - AUXILIARY GRID ONLINE")
            else:
                s.play("access_denied")
                s.say("POWER NODE OFFLINE - INSERT A POWER CELL")

    # ---------------------------------------------------------------- pickups
    def pickup(self, entity_id):
        """True = consumed (hide sprite), False = handled but stays, None = not a lobby entity."""
        s = self.state
        if entity_id == "lobby_keycard1":
            s.add_item(ITEM_KEY1)
            s.complete("get_keycard1")
            s.say("Retrieved Level-1 Keycard.")
        elif entity_id == "lobby_power_cell":
            s.add_item(ITEM_CELL)
            s.complete("get_power_cell")
            s.say("Retrieved Power Cell - install it at the Auxiliary Power Node.")
        elif entity_id == "lobby_keycard2":
            s.add_item(ITEM_KEY2)
            s.complete("get_keycard2")
            s.say("Retrieved Level-2 Keycard.")
        elif entity_id == "lobby_datachip":
            s.add_item(ITEM_CHIP)
            s.set_flag(FLAG_CHIP)
            s.complete("get_data_chip")
            self.doors.start_lockdown(LOCKDOWN_SECONDS, exempt=("launch",))
            self._alarm_timer = 0.0
            s.say("ALERT: CONTAINMENT LOCKDOWN - ALL BULKHEADS SEALING")
        elif entity_id == "lobby_log_crew":
            s.add_log("lobby_crew_log", LOG_TITLES["lobby_crew_log"])
            s.complete("read_crew_log")
            s.say("Logged: " + LOG_TITLES["lobby_crew_log"])
            return False
        elif entity_id == "lobby_log_obs":
            s.add_log("lobby_obs_log", LOG_TITLES["lobby_obs_log"])
            s.complete("read_obs_log")
            s.say("Logged: " + LOG_TITLES["lobby_obs_log"])
            return False
        else:
            return None
        s.set_flag(f"taken:{entity_id}")
        return True

    # ----------------------------------------------------------------- update
    def update(self, dt, player_pos=None):
        s = self.state
        for door, ev in self.doors.update(dt, player_pos):
            if ev == "opened":
                s.play("door_open")
            elif ev == "closed":
                s.play("door_close")
            elif ev == "lockdown_end":
                if s.has_flag(FLAG_CHIP):
                    s.set_flag(FLAG_LAUNCH_READY)
                    s.complete("survive_lockdown")
                    s.play("access_granted")
                    s.say("LOCKDOWN LIFTED - LAUNCH AIRLOCK ONLINE")
        if self.doors.lockdown_active:
            self._alarm_timer -= dt
            if self._alarm_timer <= 0.0:
                s.play("drone_alert")
                self._alarm_timer = 1.6

    @property
    def lockdown_remaining(self):
        return max(0.0, self.doors.lockdown_timer)

    # ---------------------------------------------------------------- prompts
    def prompt(self, info):
        s = self.state
        t = info.get("type")
        if t == "lobby_door":
            d = self.doors.get(info.get("id"))
            if d is None:
                return ""
            if d.is_locked:
                ok, reason = d.check_access(s.has_item, s.has_flag)
                if ok:
                    return "[E] Begin Mission Launch" if d.launch else f"[E] Unlock {d.label}"
                if d.lock_type == LOCK_CODE and not d.in_lockdown:
                    return f"[E] Enter Keypad Code - {d.label}"
                # Keep prompts short (the HUD box is fixed width); the full reason
                # is shown in the feedback banner when the player presses E.
                if d.in_lockdown:
                    return f"[E] {d.label} - LOCKDOWN"
                if d.lock_type == LOCK_KEY:
                    return f"[E] {d.label} - NEEDS {d.requires}"
                return f"[E] {d.label} - LOCKED"
            if d.launch:
                return "[E] Begin Mission Launch"
            if d.state in ("open", "opening"):
                return f"[E] Close {d.label}"
            return f"[E] Open {d.label}"
        if t == "lobby_terminal":
            tid = info.get("id")
            if tid == "mission_board":
                return "[E] Mission Board Terminal"
            if tid == "power_node":
                if s.has_flag(FLAG_POWER):
                    return "[E] Auxiliary Power Node - ONLINE"
                if s.has_item(ITEM_CELL):
                    return "[E] Install Power Cell"
                return "[E] Auxiliary Power Node - OFFLINE"
        return ""

    # ---------------------------------------------------------------- compass
    def objective_target(self):
        s = self.state
        annex = self.doors.get("annex")
        if not s.has_flag(FLAG_ACCEPTED):
            if not s.has_item(ITEM_KEY1):
                return (2.5, 1.5, "SUPPLY LOCKER - LEVEL-1 KEYCARD")
            return (9.5, 1.2, "MISSION BOARD TERMINAL")
        if not s.has_flag(FLAG_POWER):
            if annex is not None and annex.is_locked and not s.has_item(ITEM_CELL):
                return (19.5, 3.5, f"ENGINEERING ANNEX KEYPAD (CODE {ANNEX_CODE})")
            if not s.has_item(ITEM_CELL):
                return (19.5, 1.5, "POWER CELL")
            return (6.5, 6.5, "AUXILIARY POWER NODE")
        if not s.has_flag(FLAG_CHIP):
            if not s.has_item(ITEM_KEY2):
                return (9.5, 9.5, "LEVEL-2 KEYCARD (AIRLOCK BAY)")
            return (19.5, 9.5, "MISSION DATA CHIP (HANGAR)")
        if self.doors.lockdown_active:
            return (27.5, 5.5, f"LOCKDOWN - HOLD POSITION ({self.lockdown_remaining:.0f}s)")
        return (27.5, 5.5, "LAUNCH AIRLOCK")
