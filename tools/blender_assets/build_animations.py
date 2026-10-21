"""Procedural keyframed actions for the character rig (24 fps, looping).

Actions: idle, walk, sprint, crouch_idle, crouch_walk, sit, jump,
         aim_pistol, aim_rifle, reload_pistol, reload_rifle, melee_slash.

All rotations are expressed about WORLD axes (+X = character's right, so a
positive swing about X moves a hanging limb forward toward +Y) and converted to
each bone's local frame, so they don't depend on Blender's bone roll.
These are blocked-in poses/cycles, not mocap: expect to polish in the Graph Editor.
"""
import math

import bpy
from mathutils import Quaternion, Vector

FPS = 24
R = math.radians


def _local_axis(pb, world_axis):
    rest = pb.bone.matrix_local.to_3x3()
    return (rest.inverted() @ Vector(world_axis)).normalized()


class Poser:
    """Collects per-bone world-axis rotations for one frame, then keys them."""

    def __init__(self, arm):
        self.arm = arm
        self.pb = arm.pose.bones
        for b in self.pb:
            b.rotation_mode = "QUATERNION"

    def reset(self):
        for b in self.pb:
            b.rotation_quaternion = Quaternion((1, 0, 0, 0))
            b.location = (0, 0, 0)

    def rot(self, bone, x=0.0, y=0.0, z=0.0):
        """Rotate bone by x/y/z radians about world X/Y/Z (applied X, then Y, then Z)."""
        pb = self.pb[bone]
        q = Quaternion((1, 0, 0, 0))
        for ax, ang in (((1, 0, 0), x), ((0, 1, 0), y), ((0, 0, 1), z)):
            if ang:
                q = Quaternion(_local_axis(pb, ax), ang) @ q
        pb.rotation_quaternion = q @ pb.rotation_quaternion

    def move(self, bone, dx=0.0, dy=0.0, dz=0.0):
        pb = self.pb[bone]
        pb.location = pb.location + _local_axis_vec(pb, (dx, dy, dz))

    def key(self, frame):
        for b in self.pb:
            b.keyframe_insert("rotation_quaternion", frame=frame)
            b.keyframe_insert("location", frame=frame)


def _local_axis_vec(pb, v):
    return pb.bone.matrix_local.to_3x3().inverted() @ Vector(v)


def _new_action(arm, name, length):
    act = bpy.data.actions.new(name)
    act.use_fake_user = True
    arm.animation_data_create()
    arm.animation_data.action = act
    bpy.context.scene.frame_start = 0
    bpy.context.scene.frame_end = length
    return act


def _stash(arm, act):
    track = arm.animation_data.nla_tracks.new()
    track.name = act.name
    track.strips.new(act.name, int(act.frame_range[0]), act)
    arm.animation_data.action = None


def _cycle(arm, name, length, pose_fn, step=None):
    """Key pose_fn(poser, t) with t in [0,1) at `step` frame spacing; last key = first."""
    p = Poser(arm)
    act = _new_action(arm, name, length)
    step = step or max(1, length // 8)
    for f in range(0, length + 1, step):
        p.reset()
        pose_fn(p, (f % length) / length)
        p.key(f)
    _stash(arm, act)


def _pose(arm, name, pose_fn, length=24):
    """Static pose held with a gentle breathing sway (loops)."""
    p = Poser(arm)
    act = _new_action(arm, name, length)
    for f, t in ((0, 0.0), (length // 2, 0.5), (length, 1.0)):
        p.reset()
        pose_fn(p)
        breath = math.sin(t * 2 * math.pi) * R(1.2)
        p.rot("Chest", x=breath)
        p.key(f)
    _stash(arm, act)


# ------------------------------------------------------------------ locomotion
def _gait(amp_leg, amp_arm, bob, lean, knee, elbow):
    def fn(p, t):
        ph = t * 2 * math.pi
        for s, off in (("R", 0.0), ("L", math.pi)):
            a = math.sin(ph + off)
            p.rot(f"UpperLeg.{s}", x=a * amp_leg)
            p.rot(f"LowerLeg.{s}", x=-max(0.0, -math.sin(ph + off + 1.0)) * knee - 0.05)
            p.rot(f"Foot.{s}", x=-a * amp_leg * 0.4)
            p.rot(f"UpperArm.{s}", x=-a * amp_arm)
            p.rot(f"LowerArm.{s}", x=elbow + max(0.0, -a) * elbow * 0.6)
        p.rot("Spine", x=lean)
        p.rot("Chest", z=math.sin(ph) * R(5))
        p.move("Hips", dz=-abs(math.sin(ph)) * bob)
    return fn


def add_locomotion(arm):
    _cycle(arm, "idle", 48, lambda p, t: (
        p.rot("Chest", x=math.sin(t * 2 * math.pi) * R(1.5)),
        p.rot("Head", x=-math.sin(t * 2 * math.pi) * R(1.0)),
        p.rot("UpperArm.R", y=R(-3)), p.rot("UpperArm.L", y=R(3)),
        p.rot("LowerArm.R", x=R(8)), p.rot("LowerArm.L", x=R(8))), step=12)
    _cycle(arm, "walk", 32, _gait(R(30), R(24), 0.025, R(3), R(55), R(14)), step=4)
    _cycle(arm, "sprint", 20, _gait(R(52), R(48), 0.045, R(14), R(95), R(70)), step=2)

    def crouch(p):
        p.move("Hips", dz=-0.34)
        for s in ("R", "L"):
            p.rot(f"UpperLeg.{s}", x=R(75))
            p.rot(f"LowerLeg.{s}", x=R(-95))
            p.rot(f"Foot.{s}", x=R(20))
            p.rot(f"UpperArm.{s}", x=R(15))
            p.rot(f"LowerArm.{s}", x=R(30))
        p.rot("Spine", x=R(18))
        p.rot("Head", x=R(-12))
    _pose(arm, "crouch_idle", crouch)

    def crouch_walk(p, t):
        crouch(p)
        ph = t * 2 * math.pi
        for s, off in (("R", 0.0), ("L", math.pi)):
            p.rot(f"UpperLeg.{s}", x=math.sin(ph + off) * R(18))
            p.rot(f"LowerLeg.{s}", x=-max(0.0, math.sin(ph + off)) * R(25))
    _cycle(arm, "crouch_walk", 40, crouch_walk, step=5)

    def sit(p):
        p.move("Hips", dz=-0.46, dy=-0.05)
        for s in ("R", "L"):
            p.rot(f"UpperLeg.{s}", x=R(88))
            p.rot(f"LowerLeg.{s}", x=R(-88))
            p.rot(f"Foot.{s}", x=R(8))
            p.rot(f"UpperArm.{s}", x=R(25))
            p.rot(f"LowerArm.{s}", x=R(60))
        p.rot("Spine", x=R(-4))
    _pose(arm, "sit", sit)

    jump_keys = [(0, 0.0, 15, -30), (6, -0.14, 45, -70), (10, 0.0, 10, -10),
                 (18, 0.28, -15, -10), (26, 0.0, 20, -40), (34, -0.10, 40, -60), (40, 0.0, 0, 0)]
    p = Poser(arm)
    act = _new_action(arm, "jump", 40)
    for f, dz, thigh, shin in jump_keys:
        p.reset()
        p.move("Hips", dz=dz)
        for s in ("R", "L"):
            p.rot(f"UpperLeg.{s}", x=R(thigh))
            p.rot(f"LowerLeg.{s}", x=R(shin))
            p.rot(f"UpperArm.{s}", x=R(-40 if 6 < f < 26 else 10))
        p.key(f)
    _stash(arm, act)


# ---------------------------------------------------------------------- combat
def _aim_stance(p):
    p.rot("Spine", z=R(-8))
    p.rot("Chest", z=R(-8))
    p.rot("Head", z=R(8))
    for s in ("R", "L"):
        p.rot(f"UpperLeg.{s}", x=R(8 if s == "R" else -8))


def add_combat(arm):
    def aim_pistol(p):
        _aim_stance(p)
        p.rot("UpperArm.R", x=R(88), y=R(-4))
        p.rot("LowerArm.R", x=R(8))
        p.rot("UpperArm.L", x=R(80), y=R(14))
        p.rot("LowerArm.L", x=R(30), y=R(8))
    _pose(arm, "aim_pistol", aim_pistol)

    def aim_rifle(p):
        _aim_stance(p)
        p.rot("UpperArm.R", x=R(58), y=R(-8))
        p.rot("LowerArm.R", x=R(70))
        p.rot("UpperArm.L", x=R(78), y=R(18))
        p.rot("LowerArm.L", x=R(12))
        p.rot("Head", x=R(-4))
    _pose(arm, "aim_rifle", aim_rifle)

    def reload_cycle(base, mag_pose):
        def fn(p, t):
            base(p)
            k = math.sin(min(1.0, t * 1.0) * math.pi)  # 0 -> 1 -> 0
            mag_pose(p, k)
        return fn

    def pistol_mag(p, k):
        p.rot("UpperArm.L", x=R(-30) * k, y=R(-35) * k)
        p.rot("LowerArm.L", x=R(55) * k)
        p.rot("UpperArm.R", x=R(-20) * k)
        p.rot("Head", x=R(15) * k)

    def rifle_mag(p, k):
        p.rot("UpperArm.L", x=R(-35) * k, y=R(-40) * k)
        p.rot("LowerArm.L", x=R(80) * k)
        p.rot("UpperArm.R", x=R(-12) * k)
        p.rot("Head", x=R(18) * k)
        p.rot("Chest", x=R(6) * k)

    _cycle(arm, "reload_pistol", 48, reload_cycle(aim_pistol, pistol_mag), step=4)
    _cycle(arm, "reload_rifle", 60, reload_cycle(aim_rifle, rifle_mag), step=5)

    def melee(p, t):
        swing = 0.0 if t < 0.2 else (1.0 if t < 0.45 else max(0.0, 1.0 - (t - 0.45) / 0.55))
        wind = min(1.0, t / 0.2) if t < 0.45 else 0.0
        p.rot("Chest", z=R(35) * wind - R(70) * swing)
        p.rot("Spine", z=R(15) * wind - R(30) * swing)
        p.rot("UpperArm.R", x=R(70) * wind - R(10) * swing, y=R(60) * wind - R(120) * swing)
        p.rot("LowerArm.R", x=R(40))
        p.rot("UpperArm.L", x=R(35), y=R(25))
        p.move("Hips", dy=0.10 * swing)
        p.rot("UpperLeg.R", x=R(-12) * swing)
        p.rot("UpperLeg.L", x=R(20) * swing)
    _cycle(arm, "melee_slash", 24, melee, step=2)


def add_animations(arm):
    bpy.context.view_layer.objects.active = arm
    bpy.ops.object.mode_set(mode="POSE")
    bpy.context.scene.render.fps = FPS
    add_locomotion(arm)
    add_combat(arm)
    bpy.ops.object.mode_set(mode="OBJECT")
    for b in arm.pose.bones:  # return to rest pose
        b.rotation_quaternion = Quaternion((1, 0, 0, 0))
        b.location = (0, 0, 0)
    return [a.name for a in bpy.data.actions]
