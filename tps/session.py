"""Headless game session: player + weapons + targets + hit resolution (no Panda3D).

The Panda3D layer (game.py) only reads input, calls `update()`, then renders the
state and plays the returned events. Everything here is unit-testable.
"""
import math
import random
from dataclasses import dataclass
from typing import List, Optional

from .anim_state import AnimInput
from .physics import World, apply_spread
from .player import Input, PlayerController
from .testbed import build_world
from .weapons import MeleeSwing, Shot, WeaponSystem

TARGET_RESPAWN = 4.0


@dataclass
class FrameInput(Input):
    fire: bool = False
    reload: bool = False
    switch_to: Optional[int] = None


class GameSession:
    def __init__(self, world: Optional[World] = None, seed: Optional[int] = None):
        if world is None:
            world, self.colors = build_world()
        else:
            self.colors = {}
        self.world = world
        self.rng = random.Random(seed)
        self.player = PlayerController(world, 0.0, 0.0, 0.0)
        self.weapons = WeaponSystem(rng=self.rng)
        self.weapons.switch_left = 0.0
        self.respawns = []          # [time_left, box]
        self.kills = 0

    # --------------------------------------------------------------- frame
    def update(self, dt: float, fi: FrameInput) -> List[tuple]:
        ev: List[tuple] = []
        if fi.switch_to is not None:
            ev += self.weapons.switch_to(fi.switch_to)
        if fi.reload:
            ev += self.weapons.start_reload()
        was_ground = self.player.body.on_ground
        self.player.update(dt, fi)
        if self.player.body.on_ground and not was_ground:
            ev.append(("land",))
        if fi.jump and was_ground and not self.player.body.on_ground:
            ev.append(("jump",))

        shots, e = self.weapons.pull_trigger(fi.fire, self.player.aiming)
        ev += e
        for s in shots:
            ev += self._resolve_shot(s)
        swings, e = self.weapons.update(dt)
        ev += e
        for sw in swings:
            ev += self._resolve_melee(sw)
        self.player.recoil_pitch, self.player.recoil_yaw = self.weapons.consume_recoil()

        for r in list(self.respawns):
            r[0] -= dt
            if r[0] <= 0:
                b = r[1]
                b.dead, b.solid, b.hp = False, True, b.max_hp
                self.respawns.remove(r)
                ev.append(("respawn", b.name))
        return ev

    # ---------------------------------------------------------------- hits
    def _damage(self, box, amount) -> List[tuple]:
        if box is None or box.hp is None or box.dead:
            return []
        box.hp -= amount
        ev = [("hit", box.name, amount, max(0.0, box.hp))]
        if box.hp <= 0:
            box.dead, box.solid = True, False
            self.kills += 1
            self.respawns.append([TARGET_RESPAWN, box])
            ev.append(("destroyed", box.name))
        return ev

    def _resolve_shot(self, shot: Shot) -> List[tuple]:
        origin, fwd = self.player.aim_ray()
        d = apply_spread(fwd, shot.spread_deg, self.rng)
        hit = self.world.raycast(origin, d, shot.range)
        end = hit.point if hit else tuple(origin[i] + d[i] * shot.range for i in range(3))
        ev = [("tracer", origin, end)]
        if hit:
            ev.append(("impact", hit.point, hit.box.name if hit.box else "ground"))
            ev += self._damage(hit.box, shot.damage)
        return ev

    def _resolve_melee(self, sw: MeleeSwing) -> List[tuple]:
        p = self.player
        fy = p.face_yaw
        origin = (p.body.x, p.body.y, p.body.z + 1.2)
        ev = []
        # Fan of three rays (centre, ±20 degrees) so a swing is not pixel-precise.
        for off in (0.0, math.radians(20), -math.radians(20)):
            d = (-math.sin(fy + off), math.cos(fy + off), -0.12)
            hit = self.world.raycast(origin, d, sw.reach)
            if hit and hit.box is not None and hit.box.hp is not None and not hit.box.dead:
                ev.append(("impact", hit.point, hit.box.name))
                ev += self._damage(hit.box, sw.damage)
                break
        return ev

    # ----------------------------------------------------------- animation
    def anim_input(self) -> AnimInput:
        p, w = self.player, self.weapons
        wd = w.wdef
        return AnimInput(
            stance=p.stance, moving=p.moving, sprinting=p.sprinting,
            airborne=not p.body.on_ground, aiming=p.aiming, weapon_kind=wd.kind,
            aim_anim=wd.anim_aim, reloading=w.reloading, reload_anim=wd.anim_reload or "",
            meleeing=w.melee_left > 0)
