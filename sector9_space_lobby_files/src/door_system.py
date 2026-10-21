"""Door & lock system for Sector 9 (pure Python, no pygame import).

Door life-cycle (Resident-Evil style lock puzzles):

    locked  --unlock()-->  closed  --open()-->  opening  -->  open
       ^                                                       |
       +------ lock() / lockdown <-- closing <-- auto-close ---+

Lock types
    none  : never locked, just a closed door.
    key   : needs an inventory item (keycard).
    flag  : needs a story flag (e.g. 'power_online' - the grid must be restored).
    code  : needs a keypad puzzle to be solved (the engine opens the keypad UI).
    sealed: cannot be opened by the player directly; only unlock() from game logic.

A door never closes on the player: while the player stands in the doorway the
door holds open (or re-opens if it was already closing).
"""
import math

LOCK_NONE = "none"
LOCK_KEY = "key"
LOCK_FLAG = "flag"
LOCK_CODE = "code"
LOCK_SEALED = "sealed"

STATE_LOCKED = "locked"
STATE_CLOSED = "closed"
STATE_OPENING = "opening"
STATE_OPEN = "open"
STATE_CLOSING = "closing"

# A door is walkable once it is this far open.
PASSABLE_PROGRESS = 0.9


class Door:
    def __init__(self, door_id, cell, label, lock_type=LOCK_NONE, requires=None,
                 code=None, deny_message=None, auto_close=5.0, speed=1.25,
                 launch=False, orientation="h"):
        self.id = door_id
        self.cell = (int(cell[0]), int(cell[1]))
        self.label = label
        self.lock_type = lock_type
        self.requires = requires          # item name (key) or flag name (flag)
        self.code = code                  # keypad code (code)
        self.deny_message = deny_message
        self.auto_close = auto_close      # seconds open before closing; None = stay open
        self.speed = speed                # door travel per second (1.0 = full)
        self.launch = launch              # final door that launches the mission
        self.orientation = orientation

        self.state = STATE_CLOSED if lock_type == LOCK_NONE else STATE_LOCKED
        self.progress = 0.0               # 0 closed .. 1 open
        self.open_timer = 0.0
        self.relock_after_close = False   # lock as soon as it finishes closing
        self.in_lockdown = False
        self._pre_lockdown_locked = False

    # ------------------------------------------------------------------ state
    @property
    def solid(self):
        return self.progress < PASSABLE_PROGRESS

    @property
    def is_locked(self):
        return self.state == STATE_LOCKED

    @property
    def is_moving(self):
        return self.state in (STATE_OPENING, STATE_CLOSING)

    @property
    def texture_key(self):
        """Wall-texture name the raycaster should use for this door."""
        if self.state == STATE_LOCKED:
            if self.lock_type == LOCK_FLAG or self.lock_type == LOCK_SEALED:
                return "door_dark"       # unpowered / sealed bulkhead
            return "door_locked"         # red lamps: keycard / keypad
        return "door_hazard"             # powered, hazard-striped blast door

    @property
    def status_text(self):
        return {
            STATE_LOCKED: "LOCKED",
            STATE_CLOSED: "CLOSED",
            STATE_OPENING: "OPENING",
            STATE_OPEN: "OPEN",
            STATE_CLOSING: "CLOSING",
        }[self.state]

    # ----------------------------------------------------------------- access
    def check_access(self, has_item, has_flag):
        """Return (ok, reason). Does not change state."""
        if self.state != STATE_LOCKED:
            return True, ""
        if self.in_lockdown:
            return False, "CONTAINMENT LOCKDOWN ACTIVE"
        if self.lock_type == LOCK_KEY:
            if has_item(self.requires):
                return True, ""
            return False, self.deny_message or f"ACCESS DENIED - REQUIRES: {self.requires}"
        if self.lock_type == LOCK_FLAG:
            if has_flag(self.requires):
                return True, ""
            return False, self.deny_message or "ACCESS DENIED - SYSTEM OFFLINE"
        if self.lock_type == LOCK_CODE:
            return False, self.deny_message or "KEYPAD LOCK - ENTER ACCESS CODE"
        if self.lock_type == LOCK_SEALED:
            return False, self.deny_message or "SEALED - OVERRIDDEN FROM ELSEWHERE"
        return True, ""

    # ---------------------------------------------------------------- actions
    def unlock(self):
        if self.state == STATE_LOCKED:
            self.state = STATE_CLOSED
            return True
        self.relock_after_close = False
        return False

    def lock(self):
        """Lock the door. An open door closes first, then locks."""
        if self.state == STATE_CLOSED:
            self.state = STATE_LOCKED
        elif self.state in (STATE_OPEN, STATE_OPENING, STATE_CLOSING):
            self.relock_after_close = True
            if self.state != STATE_CLOSING:
                self.state = STATE_CLOSING
        return True

    def open(self):
        if self.state in (STATE_CLOSED, STATE_CLOSING):
            self.state = STATE_OPENING
            self.relock_after_close = False if not self.in_lockdown else self.relock_after_close
            return True
        return False

    def toggle(self):
        """Used on an unlocked door: open it, or close it if already open."""
        if self.state in (STATE_CLOSED, STATE_CLOSING):
            return self.open()
        if self.state in (STATE_OPEN, STATE_OPENING):
            self.state = STATE_CLOSING
            return True
        return False

    # ----------------------------------------------------------------- update
    def update(self, dt, blocked=False):
        """Advance animation. Returns 'opened' / 'closed' / None."""
        if self.state == STATE_OPENING:
            self.progress = min(1.0, self.progress + self.speed * dt)
            if self.progress >= 1.0:
                self.state = STATE_OPEN
                self.open_timer = 0.0
                return "opened"
        elif self.state == STATE_OPEN:
            self.progress = 1.0
            if self.relock_after_close:
                self.open_timer = max(self.open_timer, self.auto_close or 0.0)
            if self.auto_close is not None or self.relock_after_close:
                self.open_timer += dt
                limit = self.auto_close if self.auto_close is not None else 0.0
                if self.open_timer >= limit:
                    if blocked:
                        self.open_timer = limit      # hold open while occupied
                    else:
                        self.state = STATE_CLOSING
        elif self.state == STATE_CLOSING:
            if blocked:
                self.state = STATE_OPENING      # never crush the player
                return None
            self.progress = max(0.0, self.progress - self.speed * dt)
            if self.progress <= 0.0:
                self.state = STATE_LOCKED if self.relock_after_close else STATE_CLOSED
                self.relock_after_close = False
                return "closed"
        return None


class DoorSystem:
    """Owns every door in a level and keeps the raycaster grid in sync."""

    def __init__(self, doors=None):
        self.doors = {}
        self.by_cell = {}
        self.lockdown_timer = 0.0
        for d in doors or []:
            self.add(d)

    def add(self, door):
        self.doors[door.id] = door
        self.by_cell[door.cell] = door

    def get(self, door_id):
        return self.doors.get(door_id)

    def at(self, cell):
        return self.by_cell.get((int(cell[0]), int(cell[1])))

    @property
    def lockdown_active(self):
        return self.lockdown_timer > 0.0

    # --------------------------------------------------------------- lockdown
    def start_lockdown(self, duration, exempt=()):
        """Slam every door shut and lock it (open doors close first)."""
        self.lockdown_timer = float(duration)
        for d in self.doors.values():
            if d.id in exempt or d.in_lockdown:
                continue
            d._pre_lockdown_locked = d.is_locked or d.relock_after_close
            d.in_lockdown = True
            d.lock()

    def end_lockdown(self):
        """Restore every door to the lock state it had before the lockdown."""
        self.lockdown_timer = 0.0
        for d in self.doors.values():
            if not d.in_lockdown:
                continue
            d.in_lockdown = False
            if not d._pre_lockdown_locked:
                d.relock_after_close = False
                d.unlock()

    # ----------------------------------------------------------------- update
    def update(self, dt, player_pos=None):
        """Advance all doors. Returns list of (door, event)."""
        events = []
        for d in self.doors.values():
            blocked = False
            if player_pos is not None:
                cx, cy = d.cell[0] + 0.5, d.cell[1] + 0.5
                blocked = math.hypot(player_pos[0] - cx, player_pos[1] - cy) < 0.95
            ev = d.update(dt, blocked)
            if ev:
                events.append((d, ev))
        if self.lockdown_timer > 0.0:
            self.lockdown_timer -= dt
            if self.lockdown_timer <= 0.0:
                self.end_lockdown()
                events.append((None, "lockdown_end"))
        return events

    def sync_grid(self, level_map):
        """Write door cells into the mutable level map ('D' solid / 'O' passable)."""
        for d in self.doors.values():
            x, y = d.cell
            if 0 <= y < len(level_map) and 0 <= x < len(level_map[y]):
                level_map[y][x] = 'D' if d.solid else 'O'
