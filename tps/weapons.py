"""Weapon logic (pure Python): ammo, fire rate, reload, recoil, switching, melee.

`WeaponSystem.update()` returns events like ("fire", slot) for the audio/FX layer.
"""
import random
from dataclasses import dataclass, field
from typing import List, Optional, Tuple


@dataclass(frozen=True)
class WeaponDef:
    key: str
    name: str
    kind: str                 # "ranged" | "melee"
    model: str                # glb file in assets/models
    anim_aim: str             # animation name while aiming
    anim_reload: Optional[str]
    damage: float
    rpm: float = 60.0
    auto: bool = False
    mag_size: int = 0
    reserve_start: int = 0
    reload_time: float = 0.0
    spread_deg: float = 0.0   # hip-fire cone half-angle
    aim_spread_mult: float = 0.35
    recoil_pitch: float = 0.0  # radians of camera kick per shot
    recoil_yaw: float = 0.0
    recoil_recover: float = 6.0
    range: float = 100.0
    melee_range: float = 0.0
    melee_time: float = 0.0
    hit_time: float = 0.0     # when in the swing damage lands
    switch_time: float = 0.45


PISTOL = WeaponDef("pistol", "M1911 Pistol", "ranged", "pistol_m1911.glb", "aim_pistol", "reload_pistol",
                   damage=34, rpm=300, auto=False, mag_size=8, reserve_start=32, reload_time=1.8,
                   spread_deg=2.2, recoil_pitch=0.030, recoil_yaw=0.008, range=60)
RIFLE = WeaponDef("rifle", "Carbine", "ranged", "rifle_carbine.glb", "aim_rifle", "reload_rifle",
                  damage=22, rpm=650, auto=True, mag_size=30, reserve_start=120, reload_time=2.4,
                  spread_deg=3.0, recoil_pitch=0.018, recoil_yaw=0.010, range=150)
KUKRI = WeaponDef("kukri", "Kukri", "melee", "knife_kukri.glb", "idle", None,
                  damage=65, melee_range=1.9, melee_time=0.7, hit_time=0.28, switch_time=0.35)
DEFAULT_LOADOUT = (PISTOL, RIFLE, KUKRI)


@dataclass
class Slot:
    wdef: WeaponDef
    ammo: int = 0
    reserve: int = 0

    def __post_init__(self):
        self.ammo = self.wdef.mag_size
        self.reserve = self.wdef.reserve_start


@dataclass
class Shot:
    damage: float
    spread_deg: float
    range: float


@dataclass
class MeleeSwing:
    damage: float
    reach: float


class WeaponSystem:
    def __init__(self, loadout=DEFAULT_LOADOUT, rng: Optional[random.Random] = None):
        self.slots: List[Slot] = [Slot(w) for w in loadout]
        self.index = 0
        self.rng = rng or random.Random()
        self.cooldown = 0.0
        self.reload_left = 0.0
        self.switch_left = 0.0
        self.melee_left = 0.0
        self.melee_hit_pending = False
        self.recoil_pitch = 0.0   # accumulated camera kick (radians), recovers over time
        self.recoil_yaw = 0.0
        self.trigger_held_prev = False

    # ------------------------------------------------------------ properties
    @property
    def slot(self) -> Slot:
        return self.slots[self.index]

    @property
    def wdef(self) -> WeaponDef:
        return self.slot.wdef

    @property
    def reloading(self) -> bool:
        return self.reload_left > 0

    @property
    def busy(self) -> bool:
        return self.reloading or self.switch_left > 0 or self.melee_left > 0

    # --------------------------------------------------------------- actions
    def switch_to(self, index: int) -> List[tuple]:
        if index == self.index or not (0 <= index < len(self.slots)) or self.melee_left > 0:
            return []
        self.index = index
        self.reload_left = 0.0           # switching cancels a reload
        self.cooldown = 0.0
        self.switch_left = self.wdef.switch_time
        return [("switch", index)]

    def start_reload(self) -> List[tuple]:
        s, w = self.slot, self.wdef
        if w.kind != "ranged" or self.busy or s.ammo >= w.mag_size or s.reserve <= 0:
            return []
        self.reload_left = w.reload_time
        return [("reload_start", self.index)]

    def pull_trigger(self, held: bool, aiming: bool = False) -> Tuple[List[object], List[tuple]]:
        """Call every frame with the trigger state. Returns (shots_or_swings, events)."""
        pressed = held and not self.trigger_held_prev
        self.trigger_held_prev = held
        out, ev = [], []
        w, s = self.wdef, self.slot
        if not held or self.switch_left > 0 or self.reloading or self.cooldown > 0:
            return out, ev
        if w.kind == "melee":
            if pressed and self.melee_left <= 0:
                self.melee_left = w.melee_time
                self.melee_hit_pending = True
                ev.append(("melee", self.index))
            return out, ev
        if self.melee_left > 0 or not (w.auto or pressed):
            return out, ev
        if s.ammo <= 0:
            if pressed:
                ev.append(("dry", self.index))
                ev += self.start_reload()       # auto-reload when empty
            return out, ev
        s.ammo -= 1
        self.cooldown = 60.0 / w.rpm
        spread = w.spread_deg * (w.aim_spread_mult if aiming else 1.0)
        out.append(Shot(w.damage, spread, w.range))
        self.recoil_pitch += w.recoil_pitch
        self.recoil_yaw += self.rng.uniform(-w.recoil_yaw, w.recoil_yaw)
        ev.append(("fire", self.index))
        return out, ev

    # ---------------------------------------------------------------- update
    def update(self, dt: float) -> Tuple[List[object], List[tuple]]:
        """Advance timers. Returns (melee swings landing this frame, events)."""
        out, ev = [], []
        self.cooldown = max(0.0, self.cooldown - dt)
        self.switch_left = max(0.0, self.switch_left - dt)
        if self.reload_left > 0:
            self.reload_left -= dt
            if self.reload_left <= 0:
                self.reload_left = 0.0
                s, w = self.slot, self.wdef
                take = min(w.mag_size - s.ammo, s.reserve)
                s.ammo += take
                s.reserve -= take
                ev.append(("reload_end", self.index))
        if self.melee_left > 0:
            before = self.melee_left
            self.melee_left = max(0.0, self.melee_left - dt)
            elapsed_before = self.wdef.melee_time - before
            elapsed_after = self.wdef.melee_time - self.melee_left
            if self.melee_hit_pending and elapsed_before < self.wdef.hit_time <= elapsed_after:
                self.melee_hit_pending = False
                out.append(MeleeSwing(self.wdef.damage, self.wdef.melee_range))
        # Recoil recovery
        k = min(1.0, self.wdef.recoil_recover * dt) if self.wdef.kind == "ranged" else 1.0
        self.recoil_pitch -= self.recoil_pitch * k
        self.recoil_yaw -= self.recoil_yaw * k
        return out, ev

    def consume_recoil(self) -> Tuple[float, float]:
        """Camera layer calls this each frame for the kick to apply (pitch, yaw)."""
        p, y = self.recoil_pitch, self.recoil_yaw
        return p, y
