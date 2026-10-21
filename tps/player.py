"""Third-person player controller + orbit camera (pure Python, Panda-independent).

Angles: yaw is CCW radians about +Z (Panda's H); yaw 0 faces +Y.
forward = (-sin yaw, cos yaw), right = (cos yaw, sin yaw).
"""
import math
from dataclasses import dataclass
from typing import Tuple

from . import config as C
from .physics import Body, World


@dataclass
class Input:
    move_x: float = 0.0       # +1 = strafe right
    move_y: float = 0.0       # +1 = forward
    look_dx: float = 0.0      # pixels, +right
    look_dy: float = 0.0      # pixels, +down
    sprint: bool = False
    aim: bool = False
    jump: bool = False             # edge-triggered
    toggle_crouch: bool = False    # edge-triggered
    toggle_sit: bool = False       # edge-triggered


def _angle_diff(a: float, b: float) -> float:
    return (b - a + math.pi) % math.tau - math.pi


class PlayerController:
    def __init__(self, world: World, x=0.0, y=0.0, z=0.0):
        self.world = world
        self.body = Body(x=x, y=y, z=z)
        self.stance = "stand"
        self.cam_yaw = 0.0
        self.cam_pitch = math.radians(-8)
        self.face_yaw = 0.0
        self.sprinting = False
        self.moving = False
        self.aiming = False
        self.recoil_pitch = 0.0
        self.recoil_yaw = 0.0

    # ---------------------------------------------------------------- helpers
    @property
    def pos(self):
        return (self.body.x, self.body.y, self.body.z)

    def _set_stance(self, stance: str) -> bool:
        height = {"stand": C.STAND_HEIGHT, "crouch": C.CROUCH_HEIGHT, "sit": C.SIT_HEIGHT}[stance]
        if height > self.body.height and not self.world.can_stand(
                self.body.x, self.body.y, self.body.z, self.body.radius, height):
            return False
        self.stance, self.body.height = stance, height
        return True

    # ----------------------------------------------------------------- update
    def update(self, dt: float, inp: Input):
        b = self.body
        # Camera look
        self.cam_yaw -= inp.look_dx * C.MOUSE_SENS
        self.cam_pitch = min(C.PITCH_MAX, max(C.PITCH_MIN, self.cam_pitch - inp.look_dy * C.MOUSE_SENS))
        self.aiming = inp.aim

        # Stance changes
        if inp.toggle_crouch:
            self._set_stance("crouch" if self.stance == "stand" else "stand")
        if inp.toggle_sit and b.on_ground and not self.moving:
            self._set_stance("stand" if self.stance == "sit" else "sit")
        if inp.jump:
            if self.stance == "sit" or self.stance == "crouch":
                self._set_stance("stand")
            elif b.on_ground:
                b.jump()

        # Wish direction relative to camera
        sy, cy = math.sin(self.cam_yaw), math.cos(self.cam_yaw)
        fwd, right = (-sy, cy), (cy, sy)
        wx = fwd[0] * inp.move_y + right[0] * inp.move_x
        wy = fwd[1] * inp.move_y + right[1] * inp.move_x
        mag = math.hypot(wx, wy)
        if mag > 1.0:
            wx, wy, mag = wx / mag, wy / mag, 1.0

        if self.stance == "sit":
            speed = 0.0
        elif self.stance == "crouch":
            speed = C.CROUCH_SPEED
        elif inp.aim:
            speed = C.AIM_SPEED
        elif inp.sprint and inp.move_y > 0.3:
            speed = C.SPRINT_SPEED
        else:
            speed = C.WALK_SPEED
        self.sprinting = speed == C.SPRINT_SPEED and mag > 0.1

        control = 1.0 if b.on_ground else 0.25
        k = min(1.0, C.ACCEL * control * dt)
        b.vx += (wx * speed - b.vx) * k
        b.vy += (wy * speed - b.vy) * k
        b.step(self.world, dt)
        self.moving = math.hypot(b.vx, b.vy) > 0.3

        # Facing
        if inp.aim:
            target = self.cam_yaw
        elif self.moving:
            target = math.atan2(-b.vx, b.vy)
        else:
            target = self.face_yaw
        turn = _angle_diff(self.face_yaw, target)
        self.face_yaw += turn * min(1.0, C.TURN_RATE * dt)

    # ----------------------------------------------------------------- camera
    def view_direction(self) -> Tuple[float, float, float]:
        yaw, pitch = self.cam_yaw + self.recoil_yaw, self.cam_pitch + self.recoil_pitch
        cp = math.cos(pitch)
        return (-math.sin(yaw) * cp, math.cos(yaw) * cp, math.sin(pitch))

    def camera_transform(self):
        """Returns (position, heading_deg, pitch_deg). Pulls in when a wall is behind."""
        h = {"stand": C.CAM_HEIGHT_STAND, "crouch": C.CAM_HEIGHT_CROUCH, "sit": C.CAM_HEIGHT_SIT}[self.stance]
        dist = C.CAM_DISTANCE_AIM if self.aiming else C.CAM_DISTANCE
        shoulder = C.CAM_SHOULDER_AIM if self.aiming else C.CAM_SHOULDER
        yaw = self.cam_yaw + self.recoil_yaw
        right = (math.cos(yaw), math.sin(yaw), 0.0)
        f = self.view_direction()
        pivot = (self.body.x + right[0] * shoulder, self.body.y + right[1] * shoulder, self.body.z + h)
        want = (pivot[0] - f[0] * dist, pivot[1] - f[1] * dist, pivot[2] - f[2] * dist)
        away = (want[0] - pivot[0], want[1] - pivot[1], want[2] - pivot[2])
        hit = self.world.raycast(pivot, away, dist)
        if hit is not None:
            dist = max(C.CAM_MIN_DISTANCE, hit.dist - 0.25)
        pos = (pivot[0] - f[0] * dist, pivot[1] - f[1] * dist, pivot[2] - f[2] * dist)
        return pos, math.degrees(yaw), math.degrees(self.cam_pitch + self.recoil_pitch)

    def aim_ray(self):
        """Ray used for shooting/melee: from the camera along the view direction."""
        pos, _, _ = self.camera_transform()
        return pos, self.view_direction()
