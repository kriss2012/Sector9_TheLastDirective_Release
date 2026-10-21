"""Clothing and tactical gear matching the character sheet: black weathered jacket (open front, stand
collar, rolled sleeves, shoulder patch), black shirt, harness straps with buckles, duty belt with twin
pouches, drop-leg holster, cargo trousers with knee pads, lace-up combat boots, fingerless gloves,
wrist watch and a tactical backpack.  All pieces are skinned (auto weights) to the shared skeleton."""
from __future__ import annotations
import math
from typing import Dict, List, Sequence

import bpy
from mathutils import Vector, Euler

from .utils import (MeshBuilder, V, WeightSpec, ring_ellipse, frame_from_tangent, lerp, smoothstep, gauss, rng,
                    apply_modifiers)
from . import skeleton as SK
from .body import torso_at, torso_surface, torso_anchors, _interp, _limb_path


def _arc_ring(center: V, rx: float, ry: float, gap: float, n: int, power: float = 2.3) -> List[V]:
    """Open ring (angles -pi/2+gap .. 3pi/2-gap) i.e. everything except a front (-Y) opening."""
    pts = []
    a0, a1 = -math.pi / 2 + gap, 3 * math.pi / 2 - gap
    for i in range(n):
        a = lerp(a0, a1, i / (n - 1))
        c, s = math.cos(a), math.sin(a)
        cx = math.copysign(abs(c) ** (2 / power), c)
        sy = math.copysign(abs(s) ** (2 / power), s)
        pts.append(center + V((rx * cx, ry * sy, 0)))
    return pts


def _bustify(mb: MeshBuilder, n0: int, spec: Dict, extra: float = 0.008) -> None:
    """Apply the female chest / hip shaping to clothing verts so skin never pokes through."""
    k = spec["scale"]
    if spec["bust"] <= 0 and spec["glute"] <= 0:
        return
    for v in mb.verts_from(n0):
        x, y, z = v.co
        if spec["bust"] > 0 and y < 0:
            for sg in (-1, 1):
                g = gauss(x - sg * 0.080 * k, 0.050 * k) * gauss(z - 1.335 * k, 0.056 * k)
                v.co.y -= (spec["bust"] * 1.25 + extra) * g
                v.co.x += sg * spec["bust"] * 0.25 * g
        if spec["glute"] > 0 and y > 0:
            for sg in (-1, 1):
                g = gauss(x - sg * 0.080 * k, 0.055 * k) * gauss(z - 0.97 * k, 0.070 * k)
                v.co.y += (spec["glute"] + extra * 0.6) * g


def build_outfit(spec: Dict, T, L, female: bool, cfg, seed: int, head_info) -> Dict[str, MeshBuilder]:
    k = spec["scale"]
    G = SK.groups(T, female)
    auto = lambda bones, power=5.0, bias=None: WeightSpec.auto(bones, T, power, bias)
    rigid = WeightSpec.rigid
    nm = spec["name"]
    anchors = torso_anchors(spec)
    out: Dict[str, MeshBuilder] = {}
    TORSO_BONES = ["pelvis", "spine_01", "spine_02", "spine_03", "thigh_L", "thigh_R"]
    UPPER_BONES = ["spine_02", "spine_03", "neck", "clavicle_L", "clavicle_R", "upper_arm_L", "upper_arm_R"]
    bind_torso = auto(TORSO_BONES, 4.0, {"thigh_L": 0.4, "thigh_R": 0.4})
    bind_chest = auto(["spine_01", "spine_02", "spine_03"], 4.0)

    def torso_rings(z0, z1, infl, n=20, ns=32, gap=None, flare=0.0, y_extra=0.0):
        rings = []
        for i in range(n + 1):
            z = lerp(z0, z1, i / n)
            hw, hd, oy = _interp(anchors, z)
            t = 1 - i / n
            f = infl + flare * t * t
            if gap is None:
                rings.append(ring_ellipse(V((0, oy + y_extra, z)), V((1, 0, 0)), V((0, 1, 0)), hw + f, hd + f, ns, power=2.3))
            else:
                g = gap * (0.7 + 0.5 * t)
                rings.append(_arc_ring(V((0, oy + y_extra, z)), hw + f, hd + f, g, ns))
        return rings

    # =============================================================================== shirt
    sh = MeshBuilder(f"{nm}_Shirt")
    n0 = sh.nverts()
    sh.add_loft(torso_rings(0.97 * k, 1.515 * k, 0.007), caps=False, mat=L['shirt'], bind=bind_torso)
    _bustify(sh, n0, spec, 0.004)
    # collar band (shirt)
    nr = spec["neck_r"]
    cr = []
    for z, r in ((1.50 * k, nr * 1.55), (1.545 * k, nr * 1.28), (1.585 * k, nr * 1.22)):
        cr.append(ring_ellipse(V((0, -0.006 * k, z)), V((1, 0, 0)), V((0, 1, 0)), r, r * 1.02, 28))
    sh.add_loft(cr, caps=False, mat=L['shirt'], bind=auto(["spine_03", "neck", "head"], 5.0))
    for zi in range(7):                                                                      # buttons + placket
        z = lerp(1.47 * k, 1.04 * k, zi / 6)
        p = torso_surface(spec, z, 0.0, True, 0.011)
        sh.add_cyl(p, p + V((0, -0.003, 0)), 0.0045, 0.0045, 10, mat=L['metal_hw'], bind=bind_torso)
    out["shirt"] = sh

    # =============================================================================== jacket (open front)
    jk = MeshBuilder(f"{nm}_Jacket")
    n0 = jk.nverts()
    jk.add_loft(torso_rings(0.93 * k, 1.495 * k, 0.020, n=22, ns=40, gap=0.30, flare=0.012), caps=False, closed=False,
                mat=L['jacket'], bind=bind_torso)
    _bustify(jk, n0, spec, 0.012)
    # stand collar (open front)
    cr = []
    for z, r, gp in ((1.485 * k, nr * 2.05, 0.30), (1.530 * k, nr * 1.42, 0.38), (1.570 * k, nr * 1.40, 0.50),
                     (1.592 * k, nr * 1.46, 0.56)):
        cr.append(_arc_ring(V((0, -0.004 * k, z)), r + 0.010, r * 1.05 + 0.010, gp, 28))
    jk.add_loft(cr, caps=False, closed=False, mat=L['jacket'], bind=auto(["spine_03", "neck", "head"], 5.0, {"head": 0.7}))
    # sleeves, rolled to mid-forearm
    for sfx, sg in SK.SIDES:
        u, f = T[f"upper_arm_{sfx}"], T[f"forearm_{sfx}"]
        shd, el, wr = u["head"], u["tail"], f["tail"]
        dirv = (el - shd).normalized()
        end = el + (wr - el) * 0.50
        pts = [shd - dirv * 0.03 * k, shd + dirv * 0.01, shd + dirv * 0.14 * k, el, el.lerp(end, 0.5), end]
        ur, fr_ = spec["upper_arm_r"], spec["forearm_r"]
        # trapezius / shoulder yoke so no skin shows between collar and sleeve
        jk.add_tube_path([V((sg * 0.060 * k, 0.0, 1.488 * k)), V((sg * 0.130 * k, 0.0, 1.470 * k)), shd + V((0, 0, 0.012 * k))],
                         [0.046 * k, 0.062 * k, ur * 1.25 + 0.018], 16, mat=L['jacket'],
                         bind=auto(["spine_03", "neck", f"clavicle_{sfx}", f"upper_arm_{sfx}"], 4.0), squash=0.85,
                         ref=V((0, 1, 0)), caps=False)
        rad = [ur * 1.15 + 0.018, ur * 1.28 + 0.016, ur * 1.18 + 0.016, ur * 1.00 + 0.016, fr_ * 1.18 + 0.016, fr_ * 1.12 + 0.018]
        P, R = _limb_path(pts, rad, 3)
        jk.add_tube_path(P, R, 20, mat=L['jacket'], bind=auto(G[f"arm_{sfx}"] + ["spine_03"], 4.5, {"spine_03": 0.3}),
                         squash=0.95, ref=V((0, 1, 0)), caps=False)
        # rolled cuff (two bunched rolls)
        dd = (end - el).normalized()
        for j, dz in enumerate((0.0, 0.026)):
            p0 = end - dd * (0.034 + dz) * k
            p1 = end - dd * (0.006 + dz) * k
            jk.add_cyl(p0, p1, fr_ * 1.18 + 0.027 - 0.002 * j, fr_ * 1.18 + 0.027 - 0.002 * j, 20, mat=L['jacket'],
                       bind=auto([f"forearm_{sfx}", f"upper_arm_{sfx}"], 6.0), caps=False)
    out["jacket_core"] = jk

    # =============================================================================== pants
    pn = MeshBuilder(f"{nm}_Pants")
    pn.add_loft(torso_rings(0.84 * k, 1.075 * k, 0.012, n=10, ns=30), caps=False, mat=L['pants'],
                bind=auto(["pelvis", "spine_01", "thigh_L", "thigh_R"], 4.0))
    for sfx, sg in SK.SIDES:
        th, shn = T[f"thigh_{sfx}"], T[f"shin_{sfx}"]
        hip, knee, ank = th["head"], th["tail"], shn["tail"]
        hem = V((ank.x, ank.y - 0.002 * k, 0.120 * k))
        pts = [hip + V((0, 0, 0.12 * k)), hip, hip.lerp(knee, 0.5), knee, knee.lerp(ank, 0.45), knee.lerp(ank, 0.85), hem]
        rad = [spec["thigh_r"] * 1.12 + 0.020, spec["thigh_r"] * 1.12 + 0.016, spec["thigh_r"] * 0.98 + 0.016,
               spec["knee_r"] + 0.026, spec["calf_r"] + 0.026, spec["calf_r"] * 0.92 + 0.030, 0.082 * k]
        P, R = _limb_path(pts, rad, 4)
        # slight wrinkle bunching in the radius
        r2 = rs_wr = rng(seed, f"wr{sfx}")
        R = [r * (1 + 0.012 * math.sin(i * 1.9 + (1 if sfx == 'L' else 2))) for i, r in enumerate(R)]
        pn.add_tube_path(P, R, 22, mat=L['pants'], bind=auto(G[f"leg_{sfx}"] + ["pelvis"], 4.5, {"pelvis": 0.4}),
                         squash=1.0, ref=V((1, 0, 0)), caps=False)
        # knee pad (rigid shell + strap)
        kp = knee + V((0, -(spec["knee_r"] + 0.034), -0.040 * k))
        shin_b = auto([f"thigh_{sfx}", f"shin_{sfx}"], 6.0, {f"shin_{sfx}": 1.3})
        pn.add_box(kp, (0.092 * k, 0.034, 0.125 * k), rot=Euler((0.12, 0, 0)), mat=L['gear_nylon'], bind=shin_b, bevel=0.010)
        pn.add_box(kp + V((0, -0.016, 0.004)), (0.074 * k, 0.014, 0.095 * k), rot=Euler((0.12, 0, 0)), mat=L['polymer'],
                   bind=shin_b, bevel=0.006)
        for dz in (-0.050 * k, 0.050 * k):
            c0 = knee + V((0, 0, dz - 0.020 * k))
            pn.add_cyl(c0 - V((0, 0, 0.011)), c0 + V((0, 0, 0.011)), spec["knee_r"] + 0.034, spec["knee_r"] + 0.034, 20,
                       mat=L['webbing'], bind=shin_b, caps=False)
        # cargo pocket on outer thigh (left) / holster platform (right)
        tc = hip.lerp(knee, 0.46) + V((sg * (spec["thigh_r"] + 0.028), 0.01, 0.0))
        if sfx == "L":
            pn.add_box(tc, (0.030, 0.100 * k, 0.135 * k), mat=L['pants'], bind=auto([f"thigh_{sfx}"], 5.0), bevel=0.006)
            pn.add_box(tc + V((sg * 0.002, 0, 0.060 * k)), (0.034, 0.104 * k, 0.034 * k), mat=L['pants'],
                       bind=auto([f"thigh_{sfx}"], 5.0), bevel=0.005)                              # flap
            pn.add_cyl(tc + V((sg * 0.019, 0, 0.050 * k)), tc + V((sg * 0.024, 0, 0.050 * k)), 0.0070, 0.0070, 10,
                       mat=L['metal_hw'], bind=auto([f"thigh_{sfx}"], 5.0))
    out["pants"] = pn

    # =============================================================================== boots
    bt = MeshBuilder(f"{nm}_Boots")
    fl = spec["foot_len"]
    for sfx, sg in SK.SIDES:
        ft, tb, shn = T[f"foot_{sfx}"], T[f"toe_{sfx}"], T[f"shin_{sfx}"]
        ank = ft["head"]
        x = ank.x
        yf, yr = ank.y - fl * 0.80, ank.y + fl * 0.30
        bb = auto([f"foot_{sfx}", f"toe_{sfx}", f"shin_{sfx}"], 5.0, {f"shin_{sfx}": 0.7})
        stations = [(0.00, 0.020, 0.040), (0.10, 0.030, 0.049), (0.30, 0.042, 0.054), (0.55, 0.058, 0.053),
                    (0.75, 0.082, 0.050), (0.92, 0.090, 0.047), (1.00, 0.080, 0.043)]
        zbase = 0.026 * k
        rings = []
        for t, hh, ww in stations:
            y = lerp(yf, yr, t)
            hh *= k
            ww *= k
            rings.append(ring_ellipse(V((x, y, zbase + hh * 0.95)), V((1, 0, 0)), V((0, 0, 1)), ww, hh, 18, power=2.8))
        bt.add_loft(rings, caps=True, mat=L['boot_leather'], bind=bb)
        # toe cap
        tcp = V((x, yf + 0.030 * k, zbase + 0.034 * k))
        bt.add_sphere(tcp, (0.050 * k, 0.045 * k, 0.030 * k), 16, 10, mat=L['boot_leather'], bind=bb)
        # shaft
        sp = [V((x, ank.y + 0.004, 0.060 * k)), V((x, ank.y + 0.006, 0.125 * k)), V((x, ank.y + 0.008, 0.185 * k)),
              V((x, ank.y + 0.008, 0.228 * k))]
        sr = [0.056 * k, 0.059 * k, 0.062 * k, 0.067 * k]
        bt.add_tube_path(sp, sr, 20, mat=L['boot_leather'], bind=bb, squash=1.02, ref=V((1, 0, 0)), caps=False)
        bt.add_cyl(V((x, ank.y + 0.008, 0.222 * k)), V((x, ank.y + 0.008, 0.234 * k)), 0.071 * k, 0.071 * k, 20,
                   mat=L['boot_leather'], bind=bb, squash=1.02, caps=False)                         # padded collar
        # sole + heel
        srings = []
        for t, ww in ((0.0, 0.040), (0.08, 0.052), (0.35, 0.057), (0.6, 0.054), (0.85, 0.052), (1.0, 0.046)):
            y = lerp(yf - 0.008, yr + 0.012, t)
            srings.append(ring_ellipse(V((x, y, 0.0165 * k)), V((1, 0, 0)), V((0, 0, 1)), ww * k + 0.006, 0.0175 * k, 16, power=4.0))
        bt.add_loft(srings, caps=True, mat=L['rubber_sole'], bind=bb)
        bt.add_box(V((x, yr - 0.022 * k, 0.040 * k)), (0.090 * k, 0.050 * k, 0.026 * k), mat=L['rubber_sole'], bind=bb, bevel=0.004)
        # laces + eyelets on the instep/shaft front
        for i in range(8):
            t = i / 7
            y = lerp(yf + 0.115 * k, ank.y - 0.048 * k, t)
            z = lerp(0.060 * k, 0.195 * k, t) + (0.024 * k if t < 0.55 else 0.0) * (1 - t)
            zz = lerp(0.085 * k, 0.200 * k, t)
            yy = lerp(yf + 0.125 * k, ank.y - 0.056 * k, t)
            fy = lerp(yf + 0.120 * k, ank.y - 0.052 * k, t)
            p0, p1 = V((x - 0.030 * k, fy, zz)), V((x + 0.030 * k, fy, zz))
            bt.add_cyl(p0, p1, 0.0024, 0.0024, 6, mat=L['webbing'], bind=bb)
            for e in (-1, 1):
                bt.add_cyl(V((x + e * 0.032 * k, fy, zz)), V((x + e * 0.034 * k, fy, zz)), 0.0052, 0.0052, 10,
                           mat=L['metal_hw'], bind=bb)
        # tongue
        bt.add_box(V((x, ank.y - 0.052 * k, 0.135 * k)), (0.052 * k, 0.012, 0.150 * k), rot=Euler((-0.12, 0, 0)),
                   mat=L['boot_leather'], bind=bb, bevel=0.004)
    out["boots"] = bt

    # =============================================================================== gloves + watch
    gl = MeshBuilder(f"{nm}_Gloves")
    for sfx, sg in SK.SIDES:
        h = T[f"hand_{sfx}"]
        wr, tip = h["head"], h["tail"]
        d = (tip - wr).normalized()
        _, uu, vv = frame_from_tangent(d, V((0, 1, 0)))
        hb = auto(G[f"hand_{sfx}"] + [f"forearm_{sfx}"], 6.0, {f"forearm_{sfx}": 0.5})
        hw_ = spec["hand_w"]
        rings = []
        for t, wd_, th_ in ((-0.28, 0.58, 0.95), (0.0, 0.58, 0.95), (0.35, 0.86, 1.0), (0.7, 1.05, 1.0), (0.98, 1.05, 0.92)):
            ctr = wr + d * (spec["hand_len"] * t)
            rings.append(ring_ellipse(ctr, uu, vv, hw_ * 0.5 * wd_ + 0.003, 0.0140 * k * th_ + 0.002, 14, power=2.6))
        gl.add_loft(rings, caps=True, mat=L['glove'], bind=hb)
        for fname in ("thumb", "index", "middle", "ring", "pinky"):
            b1 = T[f"{fname}_1_{sfx}"]
            p0 = b1["head"] - (b1["tail"] - b1["head"]).normalized() * 0.004 * k
            p1 = b1["head"].lerp(b1["tail"], 0.55 if fname != "thumb" else 0.35)
            r0 = 0.0108 * k * (1.1 if fname == "thumb" else 1.0)
            gl.add_tube_path([p0, p1], [r0 * 1.05, r0 * 0.97], 10, mat=L['glove'], bind=hb, squash=0.9, ref=V((1, 0, 0)))
        # wrist strap + knuckle guard + rivets
        c0 = wr - d * 0.012 * k
        gl.add_cyl(c0, c0 + d * 0.036 * k, spec["wrist_r"] + 0.010, spec["wrist_r"] + 0.010, 20, mat=L['webbing'], bind=hb,
                   caps=False, squash=0.95)
        kc = wr + d * spec["hand_len"] * 0.78 + V((sg * 0.0, 0, 0)) + V((sg * 0.0, 0, 0))
        back = V((sg, 0, 0)) * 0.0
        gl.add_box(wr + d * spec["hand_len"] * 0.72 + vv * (0.0 if False else 0) + V((sg * 0.0165 * k, 0, 0)),
                   (0.010, 0.046 * k, 0.030 * k), mat=L['gear_nylon'], bind=hb, bevel=0.003)
        for i in range(3):
            gl.add_cyl(wr + d * spec["hand_len"] * 0.64 + V((sg * 0.0190 * k, (i - 1) * 0.012 * k, 0)),
                       wr + d * spec["hand_len"] * 0.64 + V((sg * 0.0225 * k, (i - 1) * 0.012 * k, 0)), 0.0034, 0.0034, 8,
                       mat=L['metal_hw'], bind=hb)
    # wrist watch on the left wrist
    f_l = T["forearm_L"]
    w0 = f_l["tail"] + (f_l["head"] - f_l["tail"]).normalized() * 0.045 * k
    wd = (f_l["tail"] - f_l["head"]).normalized()
    gl.add_cyl(w0 - wd * 0.011, w0 + wd * 0.011, spec["wrist_r"] + 0.0095, spec["wrist_r"] + 0.0095, 20, mat=L['watch'],
               bind=auto(["forearm_L", "hand_L"], 6.0), caps=False)
    gl.add_cyl(w0 + V((0.0, 0.0, 0.0)) + V((spec["wrist_r"] + 0.008, 0, 0)), w0 + V((spec["wrist_r"] + 0.014, 0, 0)), 0.017, 0.017,
               20, mat=L['metal_hw'], bind=auto(["forearm_L", "hand_L"], 6.0))
    out["gloves"] = gl

    # =============================================================================== harness / belts / pouches
    gr = MeshBuilder(f"{nm}_Gear")
    web = L['webbing']
    # shoulder straps over the jacket
    for sfx, sg in SK.SIDES:
        xs = sg * 0.082 * k / 0.9
        infl = 0.036
        path = [torso_surface(spec, 1.10 * k, sg * 0.070 * k, False, infl),
                torso_surface(spec, 1.26 * k, sg * 0.082 * k, False, infl),
                torso_surface(spec, 1.40 * k, sg * 0.090 * k, False, infl),
                V((sg * 0.094 * k, 0.012 * k, 1.512 * k)),
                V((sg * 0.098 * k, -0.062 * k, 1.490 * k)),
                torso_surface(spec, 1.40 * k, sg * 0.092 * k, True, infl),
                torso_surface(spec, 1.26 * k, sg * 0.088 * k, True, infl),
                torso_surface(spec, 1.10 * k, sg * 0.080 * k, True, infl)]
        P, R = _limb_path(path, [0.021 * k] * len(path), 4)
        gr.add_tube_path(P, R, 8, mat=web, bind=auto(["spine_01", "spine_02", "spine_03", "neck", f"clavicle_{sfx}"], 4.0),
                         squash=0.22, ref=V((1, 0, 0)), caps=True)
        # adjustment buckle on the front of each strap
        bp = torso_surface(spec, 1.24 * k, sg * 0.088 * k, True, infl + 0.004)
        gr.add_box(bp, (0.036 * k, 0.010, 0.050 * k), mat=L['metal_hw'], bind=bind_chest, bevel=0.002)
        gr.add_box(bp + V((0, -0.003, 0)), (0.024 * k, 0.008, 0.032 * k), mat=L['gear_nylon'], bind=bind_chest, bevel=0.002)
    # chest strap + buckle
    cz = 1.325 * k
    hw, hd, oy = _interp(anchors, cz)
    n0 = gr.nverts()
    gr.add_loft([ring_ellipse(V((0, oy, cz - 0.019 * k)), V((1, 0, 0)), V((0, 1, 0)), hw + 0.030, hd + 0.030, 36, 2.3),
                 ring_ellipse(V((0, oy, cz + 0.019 * k)), V((1, 0, 0)), V((0, 1, 0)), hw + 0.030, hd + 0.030, 36, 2.3)],
                caps=False, mat=web, bind=bind_chest)
    _bustify(gr, n0, spec, 0.022)
    bp = torso_surface(spec, cz, 0.0, True, 0.036)
    gr.add_box(bp, (0.060 * k, 0.014, 0.046 * k), mat=L['gear_nylon'], bind=bind_chest, bevel=0.004)
    gr.add_box(bp + V((0, -0.005, 0)), (0.046 * k, 0.012, 0.030 * k), mat=L['metal_hw'], bind=bind_chest, bevel=0.003)
    gr.add_box(bp + V((0, -0.011, 0)), (0.016 * k, 0.004, 0.022 * k), mat=L['gear_nylon'], bind=bind_chest, bevel=0.001)
    # lower waist strap with buckle (second strap in the reference)
    lz = 1.17 * k
    hw, hd, oy = _interp(anchors, lz)
    gr.add_loft([ring_ellipse(V((0, oy, lz - 0.024 * k)), V((1, 0, 0)), V((0, 1, 0)), hw + 0.029, hd + 0.029, 36, 2.3),
                 ring_ellipse(V((0, oy, lz + 0.024 * k)), V((1, 0, 0)), V((0, 1, 0)), hw + 0.029, hd + 0.029, 36, 2.3)],
                caps=False, mat=web, bind=bind_chest)
    bp = torso_surface(spec, lz, 0.0, True, 0.035)
    gr.add_box(bp, (0.090 * k, 0.014, 0.048 * k), mat=L['gear_nylon'], bind=bind_chest, bevel=0.004)
    gr.add_box(bp + V((0, -0.006, 0)), (0.070 * k, 0.010, 0.032 * k), mat=L['metal_hw'], bind=bind_chest, bevel=0.003)
    # duty belt
    bz = 1.045 * k
    hw, hd, oy = _interp(anchors, bz)
    belt_b = auto(["pelvis", "spine_01"], 4.0)
    gr.add_loft([ring_ellipse(V((0, oy, bz - 0.027 * k)), V((1, 0, 0)), V((0, 1, 0)), hw + 0.034, hd + 0.034, 40, 2.3),
                 ring_ellipse(V((0, oy, bz + 0.027 * k)), V((1, 0, 0)), V((0, 1, 0)), hw + 0.034, hd + 0.034, 40, 2.3)],
                caps=False, mat=L['gear_nylon'], bind=belt_b)
    bp = torso_surface(spec, bz, 0.0, True, 0.040)
    gr.add_box(bp, (0.078 * k, 0.014, 0.048 * k), mat=L['metal_hw'], bind=belt_b, bevel=0.004)
    gr.add_box(bp + V((0, -0.008, 0)), (0.050 * k, 0.008, 0.028 * k), mat=L['gear_nylon'], bind=belt_b, bevel=0.003)
    # twin magazine pouches (front) and utility pouches
    def pouch(c: V, size, rot, bones, flap=True, label=""):
        pb = auto(bones, 5.0)
        gr.add_box(c, size, rot=rot, mat=L['gear_nylon'], bind=pb, bevel=0.005)
        if flap:
            fc = c + (rot.to_matrix() @ V((0, 0, size[2] * 0.42)))
            gr.add_box(fc, (size[0] * 1.04, size[1] * 1.10, size[2] * 0.30), rot=rot, mat=L['gear_nylon'], bind=pb, bevel=0.004)
            sn = c + (rot.to_matrix() @ V((0, -size[1] * 0.58, size[2] * 0.28)))
            gr.add_cyl(sn, sn + V((0, -0.004, 0)), 0.0065, 0.0065, 10, mat=L['metal_hw'], bind=pb)
    for sg in (-1, 1):
        for i, dx in enumerate((0.040 * k, 0.092 * k)):
            p = torso_surface(spec, bz - 0.020 * k, sg * (0.050 * k + dx), True, 0.060)
            pouch(p + V((0, 0.0, -0.002)), (0.044 * k, 0.040 * k, 0.092 * k), Euler((0.0, 0, 0)), ["pelvis", "spine_01"])
    sidep = torso_surface(spec, bz - 0.030 * k, 0.16 * k, True, 0.050)
    p = V((spec["hip_w"] + 0.060, 0.030 * k, bz - 0.040 * k))
    pouch(p, (0.050 * k, 0.085 * k, 0.095 * k), Euler((0, 0, 0)), ["pelvis"])           # left utility pouch
    p = V((-(spec["hip_w"] + 0.045), 0.085 * k, bz - 0.030 * k))
    pouch(p, (0.060 * k, 0.045 * k, 0.085 * k), Euler((0, 0, 0)), ["pelvis"])            # right rear pouch
    p = torso_surface(spec, bz - 0.032 * k, 0.0, False, 0.052)
    pouch(p, (0.130 * k, 0.045 * k, 0.095 * k), Euler((0, 0, 0)), ["pelvis", "spine_01"])   # rear mag/dump pouch
    # shoulder patch (velcro) on the left upper arm
    u = T["upper_arm_L"]
    pc = u["head"].lerp(u["tail"], 0.42) + V((spec["upper_arm_r"] * 1.45 + 0.036, 0.0, 0.0))
    gr.add_box(pc, (0.008, 0.062 * k, 0.082 * k), rot=Euler((0, math.radians(-22), 0)), mat=L['patch'],
               bind=auto(["upper_arm_L", "clavicle_L"], 6.0), bevel=0.002)
    # drop-leg holster (right thigh) + straps
    th = T["thigh_R"]
    hp = th["head"].lerp(th["tail"], 0.40) + V((-(spec["thigh_r"] + 0.040), 0.005, 0))
    hb = auto(["thigh_R", "pelvis"], 6.0, {"pelvis": 0.2})
    gr.add_box(hp, (0.048, 0.086 * k, 0.175 * k), mat=L['leather_black'], bind=hb, bevel=0.006)
    gr.add_box(hp + V((0.0, -0.040 * k, 0.040 * k)), (0.052, 0.020, 0.095 * k), mat=L['leather_black'], bind=hb, bevel=0.004)
    gr.add_box(hp + V((-0.024, 0.0, 0.082 * k)), (0.010, 0.088 * k, 0.020 * k), mat=L['gear_nylon'], bind=hb, bevel=0.002)
    for dz in (0.145 * k, 0.045 * k):                                                      # leg straps with buckles
        c0 = th["head"].lerp(th["tail"], 0.40) + V((0, 0, 0.5 * (0.5 - dz / 0.30) * 0.0)) + V((0, 0, dz - 0.07 * k))
        gr.add_cyl(c0 - V((0, 0, 0.0095)), c0 + V((0, 0, 0.0095)), spec["thigh_r"] * 1.02 + 0.025, spec["thigh_r"] * 1.02 + 0.025, 22,
                   mat=web, bind=hb, caps=False)
        gr.add_box(c0 + V((-(spec["thigh_r"] + 0.028), 0.0, 0)), (0.012, 0.030, 0.028), mat=L['metal_hw'], bind=hb, bevel=0.002)
    # drop-leg hanger strap from belt
    p0 = V((-(spec["hip_w"] + 0.040), 0.020 * k, bz - 0.015 * k))
    gr.add_box(p0.lerp(hp + V((0, 0, 0.082 * k)), 0.5), (0.016, 0.026 * k, abs((hp.z + 0.082 * k) - p0.z)), mat=web, bind=hb, bevel=0.002)
    out["gear"] = gr

    # =============================================================================== backpack
    bp_ = MeshBuilder(f"{nm}_Backpack")
    pbind = auto(["spine_02", "spine_03", "spine_01"], 4.0)
    back_y = torso_surface(spec, 1.28 * k, 0.0, False, 0.034).y
    cy = back_y + 0.082 * k
    bp_.add_box(V((0, cy, 1.255 * k)), (0.300 * k, 0.150 * k, 0.400 * k), mat=L['gear_nylon'], bind=pbind, bevel=0.020)
    bp_.add_box(V((0, cy + 0.006, 1.468 * k)), (0.292 * k, 0.158 * k, 0.050 * k), mat=L['gear_nylon'], bind=pbind, bevel=0.016)   # lid
    for sg in (-1, 1):
        bp_.add_box(V((sg * 0.170 * k, cy - 0.012, 1.200 * k)), (0.052 * k, 0.110 * k, 0.215 * k), mat=L['gear_nylon'], bind=pbind, bevel=0.012)
        bp_.add_box(V((sg * 0.0, cy + 0.0, 1.0)) * 0 + V((sg * 0.115 * k, cy + 0.087 * k, 1.200 * k)), (0.092 * k, 0.026, 0.250 * k),
                    mat=L['gear_nylon'], bind=pbind, bevel=0.008)
    bp_.add_box(V((0, cy + 0.088 * k, 1.150 * k)), (0.200 * k, 0.040 * k, 0.190 * k), mat=L['gear_nylon'], bind=pbind, bevel=0.012)
    for i in range(6):                                                                                 # MOLLE rows
        z = 1.345 * k - i * 0.028 * k
        bp_.add_box(V((0, cy + 0.083 * k + 0.007, z)), (0.250 * k, 0.005, 0.0075), mat=web, bind=pbind)
    for sg in (-1, 1):                                                                                  # compression straps
        bp_.add_box(V((sg * 0.095 * k, cy + 0.083 * k, 1.28 * k)), (0.028 * k, 0.008, 0.330 * k), mat=web, bind=pbind, bevel=0.002)
        bp_.add_box(V((sg * 0.095 * k, cy + 0.090 * k, 1.17 * k)), (0.034 * k, 0.010, 0.030 * k), mat=L['metal_hw'], bind=pbind, bevel=0.002)
    bp_.add_box(V((0, cy, 1.505 * k)), (0.070 * k, 0.040 * k, 0.020 * k), mat=web, bind=pbind, bevel=0.006)        # grab handle
    bp_.add_cyl(V((0, cy + 0.083 * k, 1.440 * k)), V((0, cy + 0.083 * k, 1.060 * k)), 0.0034, 0.0034, 6, mat=L['metal_hw'], bind=pbind)  # zip line
    out["backpack"] = bp_
    return out
