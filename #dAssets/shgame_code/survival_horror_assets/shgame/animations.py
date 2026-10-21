"""Procedural animation: a tiny FK/IK pose solver + action generators.

Why a custom solver?  glTF cannot export constraints/IK, so every pose is solved here and baked into plain
quaternion/location keyframes on the pose bones (exactly what a game engine needs).

Conventions
-----------
* All pose rotations are *world-aligned deltas* ``D`` applied on top of the bone's rest orientation
  (``pose_basis = R_rest^-1 · D · R_rest``).  A child's ``D`` is expressed in the frame that follows its
  parent's pose, so flexion angles of consecutive bones simply add up.
* Character faces -Y.  Forward lean of an upright bone = ``Rx(+a)``; forward swing of a downward-pointing
  limb bone = ``Rx(-a)``.
* Weapons are held through ``X = M_rest(hand)^-1 · W_rest`` so a desired weapon world matrix ``W`` yields the
  hand pose ``W · X^-1`` and the two-bone IK solver places the wrist exactly.
"""
from __future__ import annotations
import math
from typing import Callable, Dict, List, Optional, Sequence, Tuple

import bpy
from mathutils import Vector, Matrix, Euler, Quaternion

from .utils import V, smoothstep, lerp, BuildError
from . import weapons as WP
from . import rig as RG

I3 = Matrix.Identity(3)


def Rx(a): return Euler((a, 0, 0)).to_matrix()
def Ry(a): return Euler((0, a, 0)).to_matrix()
def Rz(a): return Euler((0, 0, a)).to_matrix()
def Rxyz(x, y, z): return Euler((x, y, z)).to_matrix()


def mix(a, b, t):
    """Recursive lerp for numbers / tuples / Vectors / dicts."""
    if isinstance(a, dict):
        return {k: mix(a[k], b[k], t) for k in a}
    if isinstance(a, (int, float)):
        return a + (b - a) * t
    if isinstance(a, (tuple, list)):
        return type(a)(mix(x, y, t) for x, y in zip(a, b))
    if isinstance(a, Vector):
        return a.lerp(b, t)
    return a if t < 0.5 else b


def interp_keys(keys: Sequence[Tuple], f: float) -> Tuple:
    """Piecewise smooth interpolation of (frame, v1, v2...) tuples."""
    if f <= keys[0][0]:
        return tuple(keys[0][1:])
    for i in range(len(keys) - 1):
        a, b = keys[i], keys[i + 1]
        if a[0] <= f <= b[0]:
            t = (f - a[0]) / max(1e-6, (b[0] - a[0]))
            t = t * t * (3 - 2 * t)
            return tuple(lerp(a[j], b[j], t) for j in range(1, len(a)))
    return tuple(keys[-1][1:])


# =============================================================================== solver
class Poser:
    def __init__(self, arm: bpy.types.Object, T, k: float):
        self.arm, self.T, self.k = arm, T, k
        bones = arm.data.bones
        self.names = [b.name for b in bones]
        self.parent = {b.name: (b.parent.name if b.parent else None) for b in bones}
        self.Mrest = {n: bones[n].matrix_local.copy() for n in self.names}
        self.Rrest = {n: self.Mrest[n].to_3x3() for n in self.names}
        self.reset()

    def reset(self):
        self.D = {n: Matrix.Identity(3) for n in self.names}
        self.t = {n: V((0, 0, 0)) for n in self.names}

    # ---- forward kinematics
    def compute(self) -> Dict[str, Matrix]:
        M: Dict[str, Matrix] = {}
        for n in self.names:
            R = self.Rrest[n]
            basis = Matrix.Translation(R.inverted() @ self.t[n]) @ (R.inverted() @ self.D[n] @ R).to_4x4()
            p = self.parent[n]
            if p is None:
                M[n] = self.Mrest[n] @ basis
            else:
                M[n] = M[p] @ (self.Mrest[p].inverted() @ self.Mrest[n]) @ basis
        return M

    def _dp(self, n: str, M: Dict[str, Matrix]) -> Matrix:
        p = self.parent[n]
        if p is None:
            return Matrix.Identity(3)
        return M[p].to_3x3() @ self.Rrest[p].inverted()

    def set_world(self, n: str, Rdes: Matrix, M: Optional[Dict[str, Matrix]] = None) -> None:
        M = M or self.compute()
        Dp = self._dp(n, M)
        self.D[n] = Dp.inverted() @ Rdes @ self.Rrest[n].inverted()

    def aim(self, n: str, target_dir: Vector, roll_ref: Optional[Vector] = None) -> None:
        M = self.compute()
        Dp = self._dp(n, M)
        Rcur = Dp @ self.Rrest[n]
        y0 = Rcur @ V((0, 1, 0))
        q = y0.rotation_difference(target_dir.normalized())
        self.set_world(n, q.to_matrix() @ Rcur, M)

    # ---- two-bone IK
    def ik(self, upper: str, lower: str, end: str, target: Vector, pole: Vector,
           end_rot: Optional[Matrix] = None) -> None:
        M = self.compute()
        S = M[upper].translation.copy()
        l1 = (self.Mrest[lower].translation - self.Mrest[upper].translation).length
        l2 = (self.Mrest[end].translation - self.Mrest[lower].translation).length
        to = target - S
        d = max(abs(l1 - l2) + 1e-4, min(l1 + l2 - 1e-4, to.length))
        dirv = to.normalized()
        a = (l1 * l1 - l2 * l2 + d * d) / (2 * d)
        hgt = math.sqrt(max(0.0, l1 * l1 - a * a))
        pv = pole - dirv * pole.dot(dirv)
        if pv.length < 1e-6:
            pv = V((0, -1, 0)) - dirv * dirv.y * -1
        pv.normalize()
        E = S + dirv * a + pv * hgt
        self.aim(upper, E - S)
        self.aim(lower, (S + dirv * d) - E)
        if end_rot is not None:
            self.set_world(end, end_rot)

    # ---- write to pose bones
    def key(self, frame: float, bones: Sequence[str], prev: Dict[str, Quaternion]) -> None:
        pbs = self.arm.pose.bones
        for n in bones:
            pb = pbs[n]
            R = self.Rrest[n]
            q = (R.inverted() @ self.D[n] @ R).to_quaternion()
            if n in prev and prev[n].dot(q) < 0:
                q.negate()
            prev[n] = q.copy()
            pb.rotation_mode = 'QUATERNION'
            pb.rotation_quaternion = q
            pb.keyframe_insert('rotation_quaternion', frame=frame, group=n)
            if n in ("root", "pelvis"):
                pb.location = R.inverted() @ self.t[n]
                pb.keyframe_insert('location', frame=frame, group=n)


# =============================================================================== weapon / stance definitions
WEAPON = {
    # grip_local: palm on grip, support_local: where the left palm goes, pitch: wrist cock (deg)
    'rifle': dict(name='MachineGun', grip=V((0, 0.050, 0.0)), support=V((0.0, -0.258, 0.0)), pitch=8.0,
                  support_shift=V((0.030, 0.0, 0.0)), right_shift=V((0.0, 0.0, 0.0)),
                  mag=V((0, -0.0670, 0.020)), mag_grab=V((0.032, -0.0, -0.040)), ch=V((0, 0.082, 0.0885))),
    'pistol': dict(name='Handgun', grip=V((0, 0.030, 0.0)), support=V((0.0, 0.035, -0.040)), pitch=18.0,
                   support_shift=V((0.026, 0.0, 0.0), ), right_shift=V((0.0, 0.0, 0.0)),
                   mag=V((0, 0.0475, 0.0)), mag_grab=V((0.032, 0.0, -0.045)), ch=V((0, 0.0, 0.074))),
}


class Rigger:
    """Everything needed to generate actions for one character."""

    def __init__(self, arm, T, spec):
        self.arm, self.T, self.spec = arm, T, spec
        self.k = spec["scale"]
        self.P = Poser(arm, T, self.k)
        self.rest_ank = {s: T[f"shin_{s}"]["tail"].copy() for s in ("L", "R")}
        self.hip = {s: T[f"thigh_{s}"]["head"].copy() for s in ("L", "R")}
        self.X: Dict[str, Matrix] = {}
        for wk, w in WEAPON.items():
            Wrest = RG.grip_rest_matrix(arm, T, "R", w['grip'], w['pitch'], w['right_shift'])
            self.X[wk] = self.P.Mrest["hand_R"].inverted() @ Wrest
        self.deform = [n for n in self.P.names if T[n]["deform"] and T[n]["tag"] != "hair"]
        self.core_keys = [n for n in self.deform if T[n]["tag"] != "finger"] + ["root"]
        self.finger_keys = [n for n in self.deform if T[n]["tag"] == "finger"]
        self.hair_keys = [n for n in T if T[n]["tag"] == "hair"]

    # ------------------------------------------------------------------ pose building blocks
    def feet(self, targets: Dict[str, Tuple[Vector, float, float]]):
        """targets[side] = (ankle position offset from rest (x,y,z), foot pitch, toe pitch)."""
        P = self.P
        for s, sg in (("L", 1), ("R", -1)):
            off, pitch, toe = targets[s]
            tgt = self.rest_ank[s] + off
            pole = V((sg * 0.12, -1.0, 0.0))
            Rrest = P.Rrest[f"foot_{s}"]
            P.ik(f"thigh_{s}", f"shin_{s}", f"foot_{s}", tgt, pole, end_rot=Rx(pitch) @ Rrest)
            P.D[f"toe_{s}"] = Rx(toe)

    def arms_fk(self, up_L, fo_L, up_R, fo_R, abd=0.0):
        """Simple FK arm angles: forward swing (positive = forward), elbow flexion, abduction offset."""
        P = self.P
        P.D["upper_arm_L"] = Rx(-up_L) @ Rz(-abd)
        P.D["forearm_L"] = Rx(-fo_L)
        P.D["upper_arm_R"] = Rx(-up_R) @ Rz(abd)
        P.D["forearm_R"] = Rx(-fo_R)

    def spine(self, pitch=0.0, yaw=0.0, roll=0.0, head_pitch=0.0, head_yaw=0.0, head_roll=0.0, neck=0.4):
        P = self.P
        for n, wgt in (("spine_01", 0.28), ("spine_02", 0.34), ("spine_03", 0.38)):
            P.D[n] = Rxyz(pitch * wgt, roll * wgt, yaw * wgt)
        P.D["neck"] = Rxyz(head_pitch * neck, head_roll * neck, head_yaw * neck)
        P.D["head"] = Rxyz(head_pitch * (1 - neck), head_roll * (1 - neck), head_yaw * (1 - neck))

    def pelvis(self, t: Vector = V((0, 0, 0)), pitch=0.0, yaw=0.0, roll=0.0):
        self.P.t["pelvis"] = V(t)
        self.P.D["pelvis"] = Rxyz(pitch, roll, yaw)

    def grip_fingers(self, side: str, amount: float):
        P = self.P
        sg = 1.0 if side == "L" else -1.0
        for fname, (c1, c2) in (("index", (1.15, 1.2)), ("middle", (1.35, 1.3)), ("ring", (1.45, 1.35)), ("pinky", (1.5, 1.35)),
                                ("thumb", (0.25, 0.45))):
            for i, c in enumerate((c1, c2)):
                n = f"{fname}_{i + 1}_{side}"
                ang = c * amount * (1.0 if fname != "thumb" else 0.7)
                P.D[n] = Ry(sg * ang)

    def relax_fingers(self, side: str, amount: float = 0.22):
        P = self.P
        sg = 1.0 if side == "L" else -1.0
        for fname in ("index", "middle", "ring", "pinky"):
            for i in (1, 2):
                P.D[f"{fname}_{i}_{side}"] = Ry(sg * amount * (0.6 + 0.4 * i) * 1.0)

    # ------------------------------------------------------------------ weapon holding
    def hold_weapon(self, wkey: str, W: Matrix, left: Optional[Matrix] = None, left_mode: str = 'support',
                    left_local: Optional[Vector] = None, grip_amt: float = 1.0, left_grip_amt: float = 1.0):
        """Place the right hand from the weapon world matrix and (optionally) the left hand on a weapon-space point."""
        P = self.P
        w = WEAPON[wkey]
        Hm = W @ self.X[wkey].inverted()                       # desired hand_R pose matrix
        P.ik("upper_arm_R", "forearm_R", "hand_R", Hm.translation, V((-0.55, 0.25, -1.0)), end_rot=Hm.to_3x3())
        self.grip_fingers("R", grip_amt)
        if left_mode == 'free':
            return
        lp = left_local if left_local is not None else w['support']
        pal = W @ (lp + w['support_shift'])
        Rl = W.to_3x3() @ Rx(math.radians(-90.0 + (w['pitch'] * 0.0))) @ P.Rrest["hand_L"]
        u = P.Rrest["hand_L"].inverted() @ (self.T["socket_weapon_L"]["head"] - self.T["hand_L"]["head"])
        wrist = pal - Rl @ u
        P.ik("upper_arm_L", "forearm_L", "hand_L", wrist, V((0.55, 0.25, -1.0)), end_rot=Rl)
        self.grip_fingers("L", left_grip_amt)

    def weapon_matrix(self, pos: Vector, yaw=0.0, pitch=0.0, roll=0.0) -> Matrix:
        R = Rz(yaw) @ Rx(pitch) @ Ry(roll)
        return Matrix.Translation(pos * 1.0) @ R.to_4x4()


# =============================================================================== action writer
def _begin(arm, name):
    ad = arm.animation_data or arm.animation_data_create()
    act = bpy.data.actions.new(name)
    act.use_fake_user = True
    ad.action = act
    return act


def _end(arm, act, f0, f1, cyclic):
    act.use_frame_range = True
    act.frame_start, act.frame_end = f0, f1
    try:
        act.use_cyclic = cyclic
    except Exception:
        pass


def make_action(rg: Rigger, name: str, frames: Sequence[int], pose_fn: Callable[[Rigger, float], None],
                cyclic: bool = False, fingers: bool = True) -> bpy.types.Action:
    arm = rg.arm
    for pb in arm.pose.bones:
        pb.rotation_mode = 'QUATERNION'
        pb.rotation_quaternion = (1, 0, 0, 0)
        pb.location = (0, 0, 0)
    act = _begin(arm, name)
    prev: Dict[str, Quaternion] = {}
    keys = rg.core_keys + (rg.finger_keys if fingers else []) + rg.hair_keys
    for f in frames:
        rg.P.reset()
        pose_fn(rg, f)
        rg.P.key(f, keys, prev)
    _end(arm, act, frames[0], frames[-1], cyclic)
    return act


def push_to_nla(arm: bpy.types.Object, act: bpy.types.Action) -> None:
    ad = arm.animation_data
    tr = ad.nla_tracks.new()
    tr.name = act.name
    st = tr.strips.new(act.name, int(act.frame_range[0]), act)
    st.name = act.name
    try:
        st.use_sync_length = False
        if act.use_cyclic:
            st.repeat = 1.0
    except Exception:
        pass
    ad.action = None


# =============================================================================== poses
FPS = 30


def _breath(f, period, amp=1.0):
    return math.sin(2 * math.pi * f / period) * amp


def pose_idle(rg: Rigger, f: float, period=90.0):
    k, P = rg.k, rg.P
    b = _breath(f, period)
    rg.pelvis(V((0.004 * k * math.sin(2 * math.pi * f / (period * 2)), 0, 0.0015 * k * b)), yaw=0.012 * math.sin(2 * math.pi * f / (period * 2)))
    rg.spine(pitch=0.015 * b - 0.01, yaw=-0.01 * math.sin(2 * math.pi * f / (period * 2)), head_pitch=-0.01 * b + 0.01,
             head_yaw=0.05 * math.sin(2 * math.pi * f / (period * 2) + 1.0))
    rg.feet({"L": (V((0, 0, 0.0)), 0.0, 0.0), "R": (V((0, 0, 0.0)), 0.0, 0.0)})
    rg.arms_fk(0.03 * b, 0.12, 0.03 * -b, 0.12, abd=0.0)
    P.D["clavicle_L"] = Rz(-0.02 * b)
    P.D["clavicle_R"] = Rz(0.02 * b)
    rg.relax_fingers("L")
    rg.relax_fingers("R")
    _hair_sway(rg, f, period)


def _hair_sway(rg: Rigger, f: float, period: float, amount: float = 0.04, vel: float = 0.0):
    for i, n in enumerate(rg.hair_keys):
        ph = f / period * 2 * math.pi - i * 0.7
        rg.P.D[n] = Rxyz(amount * math.sin(ph) + vel * (i + 1) * 0.35, 0.0, amount * 0.6 * math.cos(ph * 0.7))


def foot_cycle(u: float, stance: float, stride: float, lift: float, k: float):
    """returns (forward offset, height, pitch) of the ankle for phase u in [0,1)."""
    u = u % 1.0
    if u < stance:
        s = u / stance
        fwd = stride / 2 - stride * s
        z = 0.045 * k * smoothstep(0.72, 1.0, s) * 0.8
        pitch = lerp(-0.25, 0.42, smoothstep(0.0, 1.0, s) ** 2.0) if s > 0.1 else lerp(-0.25, -0.05, s / 0.1)
    else:
        v = (u - stance) / (1 - stance)
        e = v * v * (3 - 2 * v)
        fwd = -stride / 2 + stride * e
        z = lift * math.sin(math.pi * v) ** 0.9 + 0.045 * k * (1 - smoothstep(0.0, 0.35, v)) * 0.8
        pitch = lerp(0.42, -0.25, smoothstep(0.0, 0.8, v))
    return fwd, z, pitch


def pose_locomotion(rg: Rigger, f: float, cycle: float, stride: float, lift: float, stance: float, drop: float,
                    bob: float, sway: float, lean: float, arm_sw: float, elbow: float, twist: float,
                    crouch: Optional[Vector] = None, crouch_lean: float = 0.0, arms_hold: bool = False):
    k, P = rg.k, rg.P
    ph = (f / cycle) % 1.0
    tgt = {}
    for s, off in (("L", 0.0), ("R", 0.5)):
        fwd, z, pitch = foot_cycle(ph + off, stance, stride * k, lift * k, k)
        tgt[s] = (V((0, -fwd, z)), pitch, -pitch * 0.4 if pitch > 0 else 0.0)
    pel_z = -drop * k + bob * k * math.sin(2 * math.pi * ph * 2) ** 2
    pel = V((sway * k * math.sin(2 * math.pi * ph), 0.0, pel_z))
    if crouch is not None:
        pel = pel + crouch * k
    rg.pelvis(pel, pitch=lean * 0.25, yaw=-twist * 0.8 * math.cos(2 * math.pi * ph), roll=-0.035 * math.sin(2 * math.pi * ph))
    rg.spine(pitch=lean + crouch_lean, yaw=twist * math.cos(2 * math.pi * ph), roll=0.03 * math.sin(2 * math.pi * ph),
             head_pitch=-lean * 0.8 - crouch_lean * 0.7)
    rg.feet(tgt)
    c = math.cos(2 * math.pi * ph)
    # arms: left arm back when left leg forward
    swL, swR = -arm_sw * c, arm_sw * c
    rg.arms_fk(swL, elbow + 0.5 * elbow * max(0.0, swL / max(arm_sw, 1e-6)), swR,
               elbow + 0.5 * elbow * max(0.0, swR / max(arm_sw, 1e-6)), abd=0.0)
    rg.relax_fingers("L", 0.35 if elbow > 1 else 0.22)
    rg.relax_fingers("R", 0.35 if elbow > 1 else 0.22)
    vel = 0.05 if elbow > 1 else 0.02
    _hair_sway(rg, f, cycle, 0.06, vel * math.sin(2 * math.pi * ph * 2))


def pose_walk(rg, f):
    pose_locomotion(rg, f, 32.0, 0.62, 0.075, 0.62, 0.025, 0.012, 0.014, 0.03, 0.42, 0.20, 0.10)


def pose_run(rg, f):
    pose_locomotion(rg, f, 22.0, 1.10, 0.20, 0.38, 0.06, 0.055, 0.010, 0.20, 0.80, 1.55, 0.18)


def pose_crouch_walk(rg, f):
    pose_locomotion(rg, f, 40.0, 0.36, 0.06, 0.65, 0.0, 0.006, 0.010, 0.0, 0.18, 0.5, 0.06,
                    crouch=V((0.0, 0.085, -0.34)), crouch_lean=0.45)


def _crouch_params():
    return dict(pel=V((0.0, 0.10, -0.37)), pitch=0.10, lean=0.42, head=-0.38,
                lf=(V((0.0, -0.10, 0.0)), 0.0, 0.0), rf=(V((0.0, 0.10, 0.0)), 0.0, 0.0))


def pose_crouch(rg: Rigger, f: float, enter: int = 24):
    k, P = rg.k, rg.P
    t = smoothstep(0, enter, f)
    c = _crouch_params()
    b = _breath(f, 80.0) * t
    pel = V((0, 0, 0)).lerp(c['pel'] * k, t) + V((0, 0, 0.003 * k * b))
    rg.pelvis(pel, pitch=c['pitch'] * t)
    rg.spine(pitch=c['lean'] * t + 0.02 * b, head_pitch=c['head'] * t)
    rg.feet({"L": (c['lf'][0] * k * t, 0.0, 0.0), "R": (c['rf'][0] * k * t, 0.0, 0.0)})
    rg.arms_fk(0.35 * t, 0.75 * t, 0.35 * t, 0.75 * t, abd=0.0)
    rg.relax_fingers("L", 0.3)
    rg.relax_fingers("R", 0.3)
    _hair_sway(rg, f, 80.0, 0.03)


def pose_sit(rg: Rigger, f: float, enter: int = 36):
    k, P = rg.k, rg.P
    t = smoothstep(0, enter, f)
    b = _breath(f, 90.0) * t
    pel = V((0, 0.095 * k * t, -0.455 * k * t + 0.0015 * k * b))
    rg.pelvis(pel, pitch=-0.10 * t)
    rg.spine(pitch=0.10 * t + 0.012 * b, head_pitch=-0.05 * t, yaw=0.0)
    # feet planted in front of the chair
    rg.feet({"L": (V((0.02 * k * t, -0.33 * k * t, 0.0)), 0.0, 0.0), "R": (V((-0.02 * k * t, -0.33 * k * t, 0.0)), 0.0, 0.0)})
    # hands resting on thighs
    for s, sg in (("L", 1), ("R", -1)):
        up, lo, en = f"upper_arm_{s}", f"forearm_{s}", f"hand_{s}"
        tgt_rest = rg.P.Mrest[en].translation
        tgt_sit = V((sg * 0.150 * k, -0.20 * k, 0.60 * k))
        tgt = tgt_rest.lerp(tgt_sit, t)
        roll = Ry(sg * -1 * math.radians(90.0) * -1 * t)
        Rdes = (Ry((-1 if sg > 0 else 1) * math.radians(90) * t) @ Rx(-math.radians(80) * t)) @ rg.P.Rrest[en]
        rg.P.ik(up, lo, en, tgt, V((sg * 0.6, 0.6, -0.3)), end_rot=Rdes)
        rg.relax_fingers(s, 0.15)
    _hair_sway(rg, f, 90.0, 0.02)


# ------------------------------------------------------------------ weapon poses
def _aim_params(wkey: str, k: float):
    if wkey == 'rifle':
        return dict(pos=V((-0.062 * k, -0.325 * k, 1.495 * k)), yaw=math.radians(6.0), pitch=math.radians(1.5), roll=0.0,
                    spine_yaw=math.radians(-18), spine_pitch=0.07, head=(0.14, 0.0, 0.0),
                    pel=V((0.0, 0.0, -0.025 * k)), feet=(V((0.07 * k, -0.20 * k, 0.0)), V((-0.02 * k, 0.16 * k, 0.0))))
    return dict(pos=V((-0.030 * k, -0.470 * k, 1.585 * k)), yaw=math.radians(2.0), pitch=math.radians(2.0), roll=0.0,
                spine_yaw=math.radians(-8), spine_pitch=0.05, head=(0.04, 0.0, 0.0),
                pel=V((0.0, 0.0, -0.02 * k)), feet=(V((0.06 * k, -0.17 * k, 0.0)), V((-0.04 * k, 0.12 * k, 0.0))))


def _lowready_params(wkey: str, k: float):
    if wkey == 'rifle':
        return dict(pos=V((-0.075 * k, -0.30 * k, 1.20 * k)), yaw=math.radians(8.0), pitch=math.radians(-28.0), roll=math.radians(8),
                    spine_yaw=math.radians(-12), spine_pitch=0.10, head=(0.05, 0.0, 0.0),
                    pel=V((0.0, 0.0, -0.03 * k)), feet=(V((0.07 * k, -0.20 * k, 0.0)), V((-0.02 * k, 0.16 * k, 0.0))))
    return dict(pos=V((-0.05 * k, -0.34 * k, 1.20 * k)), yaw=math.radians(4.0), pitch=math.radians(-28.0), roll=0.0,
                spine_yaw=math.radians(-6), spine_pitch=0.08, head=(0.05, 0.0, 0.0),
                pel=V((0.0, 0.0, -0.025 * k)), feet=(V((0.06 * k, -0.17 * k, 0.0)), V((-0.04 * k, 0.12 * k, 0.0))))


def _apply_weapon_stance(rg: Rigger, wkey: str, prm: Dict, recoil: float = 0.0, left_local: Optional[Vector] = None,
                         left_grip: float = 1.0, extra_left_pos: Optional[Vector] = None, left_free: bool = False,
                         b: float = 0.0):
    k = rg.k
    rg.pelvis(prm['pel'] + V((0, 0.004 * k * b, 0.0012 * k * b)), yaw=-prm['spine_yaw'] * 0.30)
    rg.spine(pitch=prm['spine_pitch'] + 0.006 * b - 0.05 * recoil, yaw=prm['spine_yaw'] * 0.70 + 0.0,
             head_pitch=prm['head'][0] + 0.2 * recoil, head_yaw=prm['spine_yaw'] * -0.55 * (1.0 if wkey == 'rifle' else 0.4))
    lf, rf = prm['feet']
    rg.feet({"L": (lf, 0.0, 0.0), "R": (rf, 0.0, 0.0)})
    pos = prm['pos'] + V((0, 0.018 * k * recoil, 0.004 * k * recoil)) + V((0, 0.002 * k * b, 0.0015 * k * b))
    W = rg.weapon_matrix(pos, prm['yaw'], prm['pitch'] + 0.045 * recoil, prm['roll'])
    # left hand
    if left_free:
        rg.hold_weapon(wkey, W, left_mode='free')
        rg.arms_fk_left_free()
    else:
        ll = left_local
        rg.hold_weapon(wkey, W, left_local=ll, left_grip_amt=left_grip)
    return W


def _left_free(rg: Rigger):
    rg.P.D["upper_arm_L"] = Rx(-0.2)
    rg.P.D["forearm_L"] = Rx(-0.5)


Rigger.arms_fk_left_free = _left_free


def pose_aim(wkey: str):
    def fn(rg: Rigger, f: float):
        k = rg.k
        b = _breath(f, 90.0)
        prm = _aim_params(wkey, k)
        _apply_weapon_stance(rg, wkey, prm, b=b)
        _hair_sway(rg, f, 90.0, 0.015)
    return fn


def pose_fire(wkey: str, length: int):
    def fn(rg: Rigger, f: float):
        k = rg.k
        t = (f % length) / length
        r = math.exp(-t * 5.0) * (1.0 if t > 0 else 1.0)
        prm = _aim_params(wkey, k)
        _apply_weapon_stance(rg, wkey, prm, recoil=r)
        rg.P.D["clavicle_R"] = Rz(0.02 * r)
        _hair_sway(rg, f, 40.0, 0.02, vel=0.05 * r)
    return fn


def pose_reload(wkey: str):
    wcfg = WEAPON[wkey]
    keys = WP.MAG_KEYS[wcfg['name']]
    n = WP.RELOAD_FRAMES

    def fn(rg: Rigger, f: float):
        k = rg.k
        A, Lr = _aim_params(wkey, k), _lowready_params(wkey, k)
        ready = smoothstep(1, 14, f) * (1 - smoothstep(n - 14, n, f))
        prm = mix(A, Lr, ready)
        W_prm = prm
        dz, dy = interp_keys(keys, f)
        mag_local = wcfg['mag'] + V((0, dy, dz)) + wcfg['mag_grab']
        mag_local = V((wcfg['mag_grab'].x * 0.0, mag_local.y, mag_local.z))
        mag_local = wcfg['mag'] + V((0, dy, dz)) + V((0, 0, wcfg['mag_grab'].z))
        sup = wcfg['support']
        if wkey == 'pistol':
            # support hand: cups the grip normally, goes to the magazine base during the swap
            grab = smoothstep(14, 28, f) * (1 - smoothstep(76, 84, f))
        else:
            grab = smoothstep(12, 26, f) * (1 - smoothstep(76, 84, f))
        rack = smoothstep(80, 84, f) * (1 - smoothstep(91, 95, f))
        ch_y = interp_keys(WP.CH_KEYS, f)[0]
        hold_local = mix(sup, mag_local, grab)
        if wkey == 'rifle':
            hold_local = mix(hold_local, wcfg['ch'] + V((0, ch_y + 0.0, 0.025)), rack)
        else:
            hold_local = mix(hold_local, V((0, 0.0, 0.074)) + V((0, 0.0, 0.0)), rack)
        _apply_weapon_stance(rg, wkey, W_prm, left_local=hold_local, left_grip=1.0 - 0.3 * grab)
        _hair_sway(rg, f, 60.0, 0.02)
    return fn


# =============================================================================== public API
def build_all_actions(arm, T, spec, cfg) -> List[str]:
    rg = Rigger(arm, T, spec)
    made: List[bpy.types.Action] = []
    nrange = lambda a, b, s: list(range(a, b + 1, s))
    made.append(make_action(rg, "Idle", nrange(0, 90, 10), pose_idle, cyclic=True))
    made.append(make_action(rg, "Walk", nrange(0, 32, 2), pose_walk, cyclic=True))
    made.append(make_action(rg, "Run", nrange(0, 22, 2), pose_run, cyclic=True))
    made.append(make_action(rg, "Crouch", nrange(0, 24, 4) + nrange(30, 110, 10), pose_crouch))
    made.append(make_action(rg, "Crouch_Walk", nrange(0, 40, 4), pose_crouch_walk, cyclic=True))
    made.append(make_action(rg, "Sit", nrange(0, 36, 4) + nrange(46, 126, 10), pose_sit))
    for wk, nm in (("rifle", "Rifle"), ("pistol", "Pistol")):
        made.append(make_action(rg, f"Aim_{nm}", nrange(0, 90, 10), pose_aim(wk), cyclic=True))
        flen = 8 if wk == 'rifle' else 10
        made.append(make_action(rg, f"Fire_{nm}", list(range(0, flen + 1)), pose_fire(wk, flen), cyclic=True))
        made.append(make_action(rg, f"Reload_{nm}", nrange(1, WP.RELOAD_FRAMES, 5) + [WP.RELOAD_FRAMES],
                                pose_reload(wk)))
    # restore rest pose and stash all actions in NLA tracks
    for pb in arm.pose.bones:
        pb.rotation_mode = 'QUATERNION'
        pb.rotation_quaternion = (1, 0, 0, 0)
        pb.location = (0, 0, 0)
    arm.animation_data.action = None
    for a in made:
        push_to_nla(arm, a)
    return [a.name for a in made]
