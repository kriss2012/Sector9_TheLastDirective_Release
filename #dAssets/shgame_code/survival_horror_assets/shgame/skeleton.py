"""Bone table shared by mesh weighting (character.py) and armature creation (rig.py).

Coordinate convention: Z up, character faces -Y, character RIGHT side = -X, LEFT = +X.
Rest pose is a relaxed A-pose (arms ~22 deg abducted) which deforms cloth better than a T-pose.
"""
from __future__ import annotations
import math
from collections import OrderedDict
from typing import Dict, List

from mathutils import Vector

V = Vector
SIDES = (("L", +1.0), ("R", -1.0))

FINGERS = {
    # name: (lateral y offset (m, male scale), lengths of the 2 segments, splay x, base along-palm fraction)
    "thumb": (-0.034, (0.036, 0.030), 0.0, 0.20),
    "index": (-0.020, (0.040, 0.030), 0.0, 0.92),
    "middle": (-0.006, (0.044, 0.032), 0.0, 0.94),
    "ring": (0.008, (0.040, 0.030), 0.0, 0.92),
    "pinky": (0.021, (0.032, 0.025), 0.0, 0.88),
}

DEFORM_CORE = ["pelvis", "spine_01", "spine_02", "spine_03", "neck", "head"]


def build_table(spec: Dict, female: bool) -> "OrderedDict[str, Dict]":
    k = spec["scale"]
    T: "OrderedDict[str, Dict]" = OrderedDict()

    def add(name, head, tail, parent, deform=True, tag=""):
        T[name] = dict(head=V(head), tail=V(tail), parent=parent, deform=deform, tag=tag)

    add("root", (0, 0, 0), (0, 0, 0.12 * k), None, deform=False)
    add("pelvis", (0, 0.0, 0.96 * k), (0, 0.0, 1.05 * k), "root")
    add("spine_01", (0, 0.0, 1.05 * k), (0, 0.0, 1.19 * k), "pelvis")
    add("spine_02", (0, 0.0, 1.19 * k), (0, 0.0, 1.33 * k), "spine_01")
    add("spine_03", (0, 0.0, 1.33 * k), (0, 0.0, 1.47 * k), "spine_02")
    add("neck", (0, 0.0, 1.47 * k), (0, -0.01 * k, 1.565 * k), "spine_03")
    add("head", (0, -0.01 * k, 1.565 * k), (0, -0.01 * k, 1.80 * k), "neck")

    sh_x = spec["shoulder_half"]
    for sfx, sg in SIDES:
        # arm
        sh = V((sg * sh_x, 0.0, 1.43 * k))
        add(f"clavicle_{sfx}", (sg * 0.03 * k, -0.015 * k, 1.455 * k), sh, "spine_03")
        d1 = V((sg * math.sin(math.radians(22)), -0.03, -math.cos(math.radians(22)))).normalized()
        el = sh + d1 * 0.300 * k
        add(f"upper_arm_{sfx}", sh, el, f"clavicle_{sfx}")
        d2 = V((sg * math.sin(math.radians(14)), -0.16, -math.cos(math.radians(14)))).normalized()
        wr = el + d2 * 0.268 * k
        add(f"forearm_{sfx}", el, wr, f"upper_arm_{sfx}")
        d3 = V((sg * math.sin(math.radians(10)), -0.06, -math.cos(math.radians(10)))).normalized()
        hl = spec["hand_len"]
        add(f"hand_{sfx}", wr, wr + d3 * hl, f"forearm_{sfx}")
        # fingers
        lat = V((0, 1, 0))
        inward = V((-sg, 0, 0))
        for fname, (yoff, segs, _splay, along) in FINGERS.items():
            sc = k
            base = wr + d3 * hl * along * (0.62 if fname != "thumb" else 1.0)
            if fname == "thumb":
                base = base + inward * 0.012 * k + lat * yoff * sc * 0.6
                dirv = (d3 * 0.55 + V((0, -1, 0)) * 0.75 + inward * 0.25).normalized()
            else:
                base = base + lat * yoff * sc + inward * 0.004 * k
                dirv = d3
            p = base
            parent = f"hand_{sfx}"
            for si, ln in enumerate(segs):
                q = p + dirv * ln * sc
                nm = f"{fname}_{si + 1}_{sfx}"
                add(nm, p, q, parent, tag="finger")
                parent = nm
                p = q
        # leg
        hx = sg * spec["hip_w"] * 0.50
        hip = V((hx, 0.0, 0.925 * k))
        knee = V((hx * 1.02, -0.012 * k, 0.505 * k))
        ankle = V((hx * 1.0, 0.012 * k, 0.085 * k))
        add(f"thigh_{sfx}", hip, knee, "pelvis")
        add(f"shin_{sfx}", knee, ankle, f"thigh_{sfx}")
        fl = spec["foot_len"]
        ball = V((hx, ankle.y - (fl * 0.52), 0.032 * k))
        toe = V((hx, ankle.y - (fl * 0.74), 0.026 * k))
        add(f"foot_{sfx}", ankle, ball, f"shin_{sfx}")
        add(f"toe_{sfx}", ball, toe, f"foot_{sfx}")

    # ---- sockets / helper (non-deforming) bones -----------------------------------------
    for sfx, sg in SIDES:
        h = T[f"hand_{sfx}"]
        palm = h["head"] + (h["tail"] - h["head"]) * 0.55
        add(f"socket_weapon_{sfx}", palm, palm + V((0, -0.05, 0)), f"hand_{sfx}", deform=False, tag="socket")
    th = T["thigh_R"]
    hol = th["head"] + (th["tail"] - th["head"]) * 0.35 + V((-0.055 * k, 0, 0))
    add("socket_holster_R", hol, hol + V((0, 0, -0.05)), "thigh_R", deform=False, tag="socket")
    hip_l = V((spec["hip_w"] * 1.02, 0.02 * k, 1.01 * k))
    add("socket_knife_L", hip_l, hip_l + V((0, 0, -0.05)), "pelvis", deform=False, tag="socket")
    add("socket_back", V((0, 0.13 * k, 1.30 * k)), V((0, 0.13 * k, 1.20 * k)), "spine_03", deform=False, tag="socket")
    add("socket_camera_focus", V((0, 0.0, 1.62 * k)), V((0, -0.05, 1.62 * k)), "spine_03", deform=False, tag="socket")

    if female:
        pts = [V((0, 0.095 * k, 1.735 * k)), V((0, 0.150 * k, 1.690 * k)), V((0, 0.185 * k, 1.585 * k)),
               V((0, 0.185 * k, 1.470 * k)), V((0, 0.170 * k, 1.350 * k))]
        parent = "head"
        for i in range(4):
            nm = f"pony_{i + 1}"
            add(nm, pts[i], pts[i + 1], parent, tag="hair")
            parent = nm
    return T


def bone_names(T) -> List[str]:
    return list(T.keys())


def groups(T, female: bool) -> Dict[str, List[str]]:
    """Convenience bone groups for auto-weighting."""
    def side(prefix, sfx):
        return [f"{prefix}_{sfx}"]
    g: Dict[str, List[str]] = {}
    for sfx in ("L", "R"):
        g[f"arm_{sfx}"] = [f"clavicle_{sfx}", f"upper_arm_{sfx}", f"forearm_{sfx}", f"hand_{sfx}"]
        g[f"hand_{sfx}"] = [f"hand_{sfx}"] + [n for n in T if n.endswith(f"_{sfx}") and T[n]["tag"] == "finger"]
        g[f"leg_{sfx}"] = [f"thigh_{sfx}", f"shin_{sfx}", f"foot_{sfx}", f"toe_{sfx}"]
        g[f"upper_arm_only_{sfx}"] = [f"clavicle_{sfx}", f"upper_arm_{sfx}", f"forearm_{sfx}"]
    g["torso"] = ["pelvis", "spine_01", "spine_02", "spine_03", "neck", "clavicle_L", "clavicle_R"]
    g["torso_hips"] = ["pelvis", "spine_01", "spine_02", "thigh_L", "thigh_R"]
    g["neck"] = ["spine_03", "neck", "head"]
    g["upper_torso_arms"] = ["spine_02", "spine_03", "neck", "clavicle_L", "clavicle_R", "upper_arm_L", "upper_arm_R"]
    return g
