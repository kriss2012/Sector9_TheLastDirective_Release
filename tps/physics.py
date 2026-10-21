"""Pure-Python collision world: AABB obstacles, character body, ray casts.

Axes: +X right, +Y forward, +Z up. No Panda3D dependency so it is unit-testable.
The environment is a list of AABBs you can replace later with your own level data.
"""
import math
import random
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

from . import config as C

Vec3 = Tuple[float, float, float]


@dataclass
class Box:
    name: str
    lo: Vec3
    hi: Vec3
    hp: Optional[float] = None      # not None => damageable target
    solid: bool = True
    max_hp: Optional[float] = None
    dead: bool = False              # destroyed targets are ignored by rays/collision

    @property
    def top(self):
        return self.hi[2]


@dataclass
class RayHit:
    dist: float
    point: Vec3
    box: Optional[Box]              # None => ground plane


class World:
    def __init__(self, ground_z: float = 0.0):
        self.ground_z = ground_z
        self.boxes: List[Box] = []

    def add_box(self, name, lo, hi, hp=None) -> Box:
        b = Box(name, tuple(lo), tuple(hi), hp, max_hp=hp)
        self.boxes.append(b)
        return b

    # ------------------------------------------------------------- queries
    @staticmethod
    def _circle_overlaps_box(x, y, r, b: Box) -> bool:
        cx = min(max(x, b.lo[0]), b.hi[0])
        cy = min(max(y, b.lo[1]), b.hi[1])
        return (x - cx) ** 2 + (y - cy) ** 2 < r * r

    def floor_height(self, x, y, r, ref_z) -> float:
        """Highest walkable surface under the circle that is reachable from ref_z."""
        h = self.ground_z
        for b in self.boxes:
            if b.solid and b.top <= ref_z + C.STEP_HEIGHT and self._circle_overlaps_box(x, y, r, b):
                h = max(h, b.top)
        return h

    def blocked(self, x, y, z, r, height) -> bool:
        """Is a body with feet at z blocked horizontally at (x, y)?"""
        for b in self.boxes:
            if not b.solid:
                continue
            if b.top > z + C.STEP_HEIGHT and b.lo[2] < z + height and self._circle_overlaps_box(x, y, r, b):
                return True
        return False

    def can_stand(self, x, y, z, r, new_height) -> bool:
        for b in self.boxes:
            if b.solid and b.lo[2] > z and b.lo[2] < z + new_height and self._circle_overlaps_box(x, y, r, b):
                return False
        return True

    # ------------------------------------------------------------ ray cast
    def raycast(self, origin: Vec3, direction: Vec3, max_dist: float) -> Optional[RayHit]:
        d = _norm(direction)
        best: Optional[RayHit] = None
        for b in self.boxes:
            if b.dead:
                continue
            t = _ray_box(origin, d, b.lo, b.hi)
            if t is not None and t <= max_dist and (best is None or t < best.dist):
                best = RayHit(t, _add(origin, _mul(d, t)), b)
        if d[2] < -1e-9:  # ground plane
            t = (self.ground_z - origin[2]) / d[2]
            if 0 <= t <= max_dist and (best is None or t < best.dist):
                best = RayHit(t, _add(origin, _mul(d, t)), None)
        return best


@dataclass
class Body:
    """Character capsule approximated as a vertical cylinder (feet position)."""
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0
    vx: float = 0.0
    vy: float = 0.0
    vz: float = 0.0
    radius: float = C.BODY_RADIUS
    height: float = C.STAND_HEIGHT
    on_ground: bool = False

    def step(self, world: World, dt: float):
        # Horizontal: resolve each axis separately so the body slides along walls.
        nx = self.x + self.vx * dt
        if world.blocked(nx, self.y, self.z, self.radius, self.height):
            self.vx = 0.0
        else:
            self.x = nx
        ny = self.y + self.vy * dt
        if world.blocked(self.x, ny, self.z, self.radius, self.height):
            self.vy = 0.0
        else:
            self.y = ny
        # Vertical
        old_z = self.z
        self.vz -= C.GRAVITY * dt
        self.z += self.vz * dt
        floor = world.floor_height(self.x, self.y, self.radius, old_z)
        if self.z <= floor:
            self.z = floor
            self.vz = 0.0
            self.on_ground = True
        else:
            self.on_ground = False
        # Head bump
        for b in world.boxes:
            if (b.solid and self.vz > 0 and b.lo[2] >= old_z + self.height - 0.05
                    and b.lo[2] < self.z + self.height and world._circle_overlaps_box(self.x, self.y, self.radius, b)):
                self.z = b.lo[2] - self.height
                self.vz = 0.0

    def jump(self):
        if self.on_ground:
            self.vz = C.JUMP_SPEED
            self.on_ground = False


# -------------------------------------------------------------- vector utils
def _add(a, b): return (a[0] + b[0], a[1] + b[1], a[2] + b[2])
def _mul(a, k): return (a[0] * k, a[1] * k, a[2] * k)
def _dot(a, b): return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]
def _cross(a, b): return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


def _norm(a):
    n = math.sqrt(_dot(a, a)) or 1.0
    return (a[0] / n, a[1] / n, a[2] / n)


def _ray_box(o, d, lo, hi) -> Optional[float]:
    tmin, tmax = 0.0, float("inf")
    for i in range(3):
        if abs(d[i]) < 1e-12:
            if o[i] < lo[i] or o[i] > hi[i]:
                return None
        else:
            t1, t2 = (lo[i] - o[i]) / d[i], (hi[i] - o[i]) / d[i]
            if t1 > t2:
                t1, t2 = t2, t1
            tmin, tmax = max(tmin, t1), min(tmax, t2)
            if tmin > tmax:
                return None
    return tmin


def apply_spread(direction: Vec3, spread_deg: float, rng: random.Random) -> Vec3:
    """Random cone deviation around `direction` (uniform within the cone)."""
    if spread_deg <= 0:
        return _norm(direction)
    fwd = _norm(direction)
    helper = (0, 0, 1) if abs(fwd[2]) < 0.99 else (1, 0, 0)
    right = _norm(_cross(fwd, helper))
    up = _cross(right, fwd)
    ang = math.radians(spread_deg) * math.sqrt(rng.random())
    rot = rng.random() * math.tau
    s = math.tan(ang)
    return _norm(_add(fwd, _add(_mul(right, s * math.cos(rot)), _mul(up, s * math.sin(rot)))))
