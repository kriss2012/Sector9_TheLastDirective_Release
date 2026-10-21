"""Skin-level anatomy: torso, limbs, hands, parametric head, eyes, brows, hair, beard.

NOTE ON FACIAL LIKENESS
-----------------------
The head is a *parametric* face (landmark-driven Gaussian displacements on a dense ellipsoid mesh).
The proportions come from the dimension tables in ``config.CHARACTERS`` (round broad face, heavy brow,
broad nose, full moustache + short beard for the male reference). Procedural code can NOT reproduce a
specific person's likeness: that requires photogrammetry / manual sculpting (see README, "What code cannot do").
"""
from __future__ import annotations
import math
from typing import Dict, List, Sequence, Tuple

import bmesh
import bpy
from mathutils import Vector, Euler, Matrix
from mathutils.noise import noise as mnoise

from .utils import (MeshBuilder, V, WeightSpec, ring_ellipse, frame_from_tangent, smoothstep, gauss, lerp, rng)
from . import skeleton as SK


# ====================================================================================== torso
def _interp(anchors: Sequence[Tuple[float, ...]], z: float) -> Tuple[float, ...]:
    if z <= anchors[0][0]:
        return anchors[0][1:]
    if z >= anchors[-1][0]:
        return anchors[-1][1:]
    for i in range(len(anchors) - 1):
        a, b = anchors[i], anchors[i + 1]
        if a[0] <= z <= b[0]:
            t = (z - a[0]) / (b[0] - a[0])
            t = t * t * (3 - 2 * t)
            return tuple(lerp(a[j], b[j], t) for j in range(1, len(a)))
    return anchors[-1][1:]


def torso_anchors(spec: Dict) -> List[Tuple[float, float, float, float]]:
    """(z, half_width, half_depth, y_offset) with z in metres (already scaled)."""
    k = spec["scale"]
    hw, hd = spec["hip_w"], spec["hip_d"]
    ww, wd = spec["waist_w"], spec["waist_d"]
    cw, cd = spec["chest_w"], spec["chest_d"]
    nr = spec["neck_r"]
    return [
        (0.88 * k, hw * 0.86, hd * 0.86, 0.004),
        (0.96 * k, hw * 1.00, hd * 1.00, 0.008),
        (1.06 * k, lerp(hw, ww, 0.55), lerp(hd, wd, 0.55), 0.004),
        (1.14 * k, ww, wd, 0.0),
        (1.24 * k, lerp(ww, cw, 0.55), lerp(wd, cd, 0.6), -0.004),
        (1.33 * k, cw * 0.99, cd * 1.00, -0.006),
        (1.40 * k, cw * 0.99, cd * 0.98, -0.004),
        (1.44 * k, cw * 0.90, cd * 0.86, 0.0),
        (1.475 * k, cw * 0.58, cd * 0.62, 0.0),
        (1.505 * k, nr * 2.3, nr * 1.95, 0.0),
        (1.54 * k, nr * 1.2, nr * 1.15, -0.005),
    ]


def torso_at(spec: Dict, z: float) -> Tuple[float, float, float]:
    return _interp(torso_anchors(spec), z)


def torso_surface(spec: Dict, z: float, x: float, front: bool = True, inflate: float = 0.0) -> V:
    """Point on the torso super-ellipse surface (power ~2.3) at height z and lateral x."""
    hw, hd, oy = torso_at(spec, z)
    hw += inflate
    hd += inflate
    xr = max(-0.999, min(0.999, x / hw))
    yy = hd * (1 - abs(xr) ** 2.3) ** (1 / 2.3)
    return V((x, oy + (-yy if front else yy), z))


# ====================================================================================== limbs
def _limb_path(points: Sequence[V], radii: Sequence[float], subdiv: int = 4):
    """Subdivide a polyline into ``subdiv`` rings per segment with linearly interpolated radius."""
    P, R = [], []
    for i in range(len(points) - 1):
        for j in range(subdiv):
            t = j / subdiv
            P.append(points[i].lerp(points[i + 1], t))
            R.append(lerp(radii[i], radii[i + 1], t))
    P.append(points[-1])
    R.append(radii[-1])
    return P, R


def build_body(spec: Dict, T, L, col, female: bool, cfg) -> bpy.types.Object:
    k = spec["scale"]
    name = f"{spec['name']}_Body"
    mb = MeshBuilder(name)
    skin = L['skin_female' if female else 'skin_male']
    G = SK.groups(T, female)
    ns = cfg.limb_sides
    auto = lambda bones, power=5.0, bias=None: WeightSpec.auto(bones, T, power, bias)

    # ------------------------------------------------------------ torso
    anchors = torso_anchors(spec)
    z0, z1 = anchors[0][0], anchors[-1][0]
    rings, N = [], 22
    for i in range(N + 1):
        z = lerp(z0, z1, i / N)
        hw, hd, oy = _interp(anchors, z)
        rings.append(ring_ellipse(V((0, oy, z)), V((1, 0, 0)), V((0, 1, 0)), hw, hd, 28, power=2.3))
    n0 = mb.nverts()
    mb.add_loft(rings, caps=True, mat=skin, bind=auto(G["torso"] + ["thigh_L", "thigh_R"], 4.0))
    # gender-specific shaping ------------------------------------------------------------------
    for v in mb.verts_from(n0):
        x, y, z = v.co
        if spec["bust"] > 0 and y < 0:
            for sg in (-1, 1):
                g = gauss(x - sg * 0.080 * k, 0.045 * k) * gauss(z - 1.335 * k, 0.050 * k)
                v.co.y -= spec["bust"] * g * 1.25
                v.co.x += sg * spec["bust"] * 0.25 * g
        if spec["glute"] > 0 and y > 0:
            for sg in (-1, 1):
                g = gauss(x - sg * 0.080 * k, 0.050 * k) * gauss(z - 0.97 * k, 0.065 * k)
                v.co.y += spec["glute"] * g
        elif spec["glute"] > 0 and z < 1.0 * k and y > 0:
            pass
    # pecs / abs definition for the male
    if not female:
        for v in mb.verts_from(n0):
            x, y, z = v.co
            if y < 0:
                for sg in (-1, 1):
                    g = gauss(x - sg * 0.085, 0.050) * gauss(z - 1.36 * k, 0.045)
                    v.co.y -= 0.007 * g
    # ------------------------------------------------------------ neck
    nk = T["neck"]
    neck_pts = [V((0, 0.0, 1.47 * k)), V((0, -0.006 * k, 1.53 * k)), V((0, -0.012 * k, 1.585 * k))]
    mb.add_tube_path(neck_pts, [spec["neck_r"] * 1.35, spec["neck_r"] * 1.02, spec["neck_r"] * 0.96], 20, mat=skin,
                     bind=auto(G["neck"], 5.0), squash=0.95, ref=V((1, 0, 0)))
    # ------------------------------------------------------------ arms
    for sfx, sg in SK.SIDES:
        c, u, f, h = T[f"clavicle_{sfx}"], T[f"upper_arm_{sfx}"], T[f"forearm_{sfx}"], T[f"hand_{sfx}"]
        sh, el, wr = u["head"], u["tail"], f["tail"]
        dirv = (el - sh).normalized()
        pts = [sh - dirv * 0.035 * k + V((-sg * 0.012 * k, 0, 0.012 * k)), sh + dirv * 0.03 * k, el, wr]
        pts = [sh + V((-sg * 0.045 * k, 0.0, 0.03 * k)), sh, sh + dirv * 0.12 * k, el, el + (wr - el) * 0.40, wr]
        rad = [spec["upper_arm_r"] * 1.05, spec["upper_arm_r"] * 1.28, spec["upper_arm_r"] * 1.12, spec["upper_arm_r"] * 0.88,
               spec["forearm_r"] * 1.12, spec["wrist_r"] * 1.0]
        P, R = _limb_path(pts, rad, 4)
        mb.add_tube_path(P, R, ns, mat=skin, bind=auto(G[f"arm_{sfx}"] + [f"spine_03"], 4.5, bias={f"spine_03": 0.35}),
                         squash=0.92, ref=V((0, 1, 0)))
        # ---- hand
        wrp, tip = h["head"], h["tail"]
        d = (tip - wrp).normalized()
        _, uu, vv = frame_from_tangent(d, V((0, 1, 0)))
        sc = k
        hw_ = spec["hand_w"]
        palm_rings = []
        for t, wd_, th_ in ((0.0, 0.50, 0.55), (0.35, 0.80, 0.60), (0.7, 1.0, 0.55), (1.0, 1.0, 0.45)):
            ctr = wrp + d * (spec["hand_len"] * t * 0.95)
            palm_rings.append(ring_ellipse(ctr, uu, vv, hw_ * 0.5 * wd_, 0.0135 * sc * th_ / 0.55, 12, power=2.6))
        mb.add_loft(palm_rings, caps=True, mat=skin, bind=auto(G[f"hand_{sfx}"], 6.0))
        for fname in ("thumb", "index", "middle", "ring", "pinky"):
            b1, b2 = T[f"{fname}_1_{sfx}"], T[f"{fname}_2_{sfx}"]
            pts = [b1["head"] - (b1["tail"] - b1["head"]).normalized() * 0.006 * sc, b1["head"], b1["tail"], b2["tail"]]
            r0 = 0.0098 * sc * (1.1 if fname == "thumb" else 1.0)
            rad = [r0 * 1.05, r0, r0 * 0.88, r0 * 0.68]
            mb.add_tube_path(pts, rad, max(6, cfg.finger_sides), mat=skin, bind=auto(G[f"hand_{sfx}"], 8.0), squash=0.88,
                             ref=V((1, 0, 0)))
    # ------------------------------------------------------------ legs
    for sfx, sg in SK.SIDES:
        th, sh_, ft, tb = T[f"thigh_{sfx}"], T[f"shin_{sfx}"], T[f"foot_{sfx}"], T[f"toe_{sfx}"]
        hip, knee, ank = th["head"], th["tail"], sh_["tail"]
        pts = [hip + V((0, 0, 0.05 * k)), hip, hip.lerp(knee, 0.5), knee, knee.lerp(ank, 0.30), knee.lerp(ank, 0.7), ank]
        rad = [spec["thigh_r"] * 1.05, spec["thigh_r"] * 1.08, spec["thigh_r"] * 0.92, spec["knee_r"],
               spec["calf_r"] * 1.05, spec["calf_r"] * 0.78, spec["ankle_r"]]
        P, R = _limb_path(pts, rad, 4)
        mb.add_tube_path(P, R, ns, mat=skin, bind=auto(G[f"leg_{sfx}"] + ["pelvis"], 4.5, bias={"pelvis": 0.4}),
                         squash=1.0, ref=V((1, 0, 0)))
        # foot (hidden by boots but needed for deformation reference / barefoot variants)
        fp = [ank, ft["tail"], tb["tail"]]
        mb.add_tube_path(fp, [spec["ankle_r"] * 1.1, spec["ankle_r"] * 0.95, spec["ankle_r"] * 0.55], 12, mat=skin,
                         bind=auto([f"foot_{sfx}", f"toe_{sfx}", f"shin_{sfx}"], 5.0), squash=0.7, ref=V((1, 0, 0)))
    mb.recalc_normals()
    return mb


# ====================================================================================== head
class HeadBuild:
    pass


def build_head(spec: Dict, T, L, col, female: bool, cfg):
    """Returns (MeshBuilder head, info dict with landmark data for hair/beard/clothing)."""
    k = spec["scale"]
    hp = spec["head"]
    W, D, H = hp["width"], hp["depth"], hp["height"]
    a, b, cz = W / 2, D / 2, H / 2
    h = H / 0.232
    c = V((0.0, -0.010 * k + 0.014, 1.80 * k - cz))
    skin = L['skin_female' if female else 'skin_male']
    lips = L['lips_female' if female else 'lips_male']
    mouth = L['mouth']
    mb = MeshBuilder(f"{spec['name']}_Head")
    mb.slot(skin), mb.slot(lips), mb.slot(mouth)

    eye_x = 0.0345 * (a / 0.079) * (0.97 if female else 1.0)
    LM = dict(eye_z=0.003 * h, brow_z=0.027 * h, nose_z=-0.040 * h, mouth_z=-0.071 * h, chin_z=-0.103 * h)
    jaw, cheek, brow, nw, nl, lip, chin, fh = (hp["jaw"], hp["cheek"], hp["brow"], hp["nose_w"], hp["nose_len"],
                                              hp["lip"], hp["chin"], hp["forehead"])

    def shape(p: V) -> V:
        """Base ellipsoid shaping + landmark displacement. p is relative to the head centre."""
        x, y, z = p
        X, Y, Z = x / a, y / b, z / cz
        # lower-face taper & chin recession
        if Z < 0:
            t = smoothstep(0.0, -1.0, Z)
            x *= 1.0 - (0.30 / max(0.5, jaw)) * t ** 1.5
            y *= 1.0 - 0.06 * t
            if Y < 0:   # square jaw corners
                x *= 1.0 + 0.05 * (jaw - 0.9) * gauss(Z + 0.45, 0.25)
        ax = abs(x)
        n = V((x / a ** 2, y / b ** 2, z / cz ** 2)).normalized()
        fm = smoothstep(-0.10 * b, -0.60 * b, y)               # front-facing mask
        d, dy = 0.0, 0.0
        # brow ridge & forehead
        d += brow * 0.0070 * gauss(z - LM['brow_z'], 0.011 * h) * smoothstep(0.066, 0.030, ax) * fm
        d += 0.0045 * fh * gauss(z - 0.058 * h, 0.030 * h) * smoothstep(0.070, 0.020, ax) * fm
        # eye sockets + lid ridges
        sock = gauss(ax - eye_x, 0.0145) * gauss(z - LM['eye_z'], 0.0125 * h) * fm
        d -= 0.0090 * sock
        d += 0.0030 * gauss(ax - eye_x, 0.015) * gauss(z - (LM['eye_z'] + 0.014 * h), 0.0045 * h) * fm
        d += 0.0020 * gauss(ax - eye_x, 0.013) * gauss(z - (LM['eye_z'] - 0.012 * h), 0.0045 * h) * fm
        # nose: bridge, tip, wings, nostrils
        dy += nl * 0.0130 * gauss(x, 0.0085) * gauss(z - (-0.010 * h), 0.022 * h) * fm
        dy += nl * 0.0230 * gauss(x, 0.0120 * nw) * gauss(z - LM['nose_z'], 0.0120 * h) * fm
        dy += 0.0090 * gauss(ax - 0.0165 * nw, 0.0075 * nw) * gauss(z - (LM['nose_z'] - 0.005 * h), 0.0095 * h) * fm
        dy -= 0.0050 * gauss(ax - 0.0090, 0.0042) * gauss(z - (LM['nose_z'] - 0.011 * h), 0.0040 * h) * fm
        # cheeks, jaw corners
        d += cheek * 0.0055 * gauss(ax - 0.054 * (a / 0.079), 0.020) * gauss(z + 0.010 * h, 0.022 * h) * fm
        d += 0.0060 * (jaw - 0.8) * gauss(ax - 0.066 * (a / 0.079), 0.016) * gauss(z + 0.062 * h, 0.026 * h) * fm
        # lips (upper / lower), mouth line, under-lip dent, chin
        mz = LM['mouth_z']
        lw = lip
        d += lw * 0.0048 * gauss(z - (mz + 0.0075 * h), 0.0050 * h) * smoothstep(0.034, 0.010, ax) * fm
        d += lw * 0.0060 * gauss(z - (mz - 0.0085 * h), 0.0062 * h) * smoothstep(0.030, 0.008, ax) * fm
        d -= 0.0032 * gauss(z - mz, 0.0014 * h) * smoothstep(0.038, 0.022, ax) * fm
        d -= 0.0030 * gauss(z - (mz - 0.0250 * h), 0.0060 * h) * smoothstep(0.030, 0.012, ax) * fm
        d += 0.0030 * gauss(z - (mz + 0.0200 * h), 0.0060 * h) * smoothstep(0.020, 0.0, ax) * fm   # philtrum pad
        dy += chin * 0.0085 * gauss(x, 0.024) * gauss(z - LM['chin_z'], 0.014 * h) * fm
        # brow-to-nose bridge dip
        d -= 0.0030 * gauss(x, 0.010) * gauss(z - 0.012 * h, 0.008 * h) * fm
        return V((x, y - dy, z)) + n * d

    nu = cfg.head_segments
    nv = int(nu * 0.75)
    bm = mb.bm
    ret = bmesh.ops.create_uvsphere(bm, u_segments=nu, v_segments=nv, radius=1.0)
    verts = ret['verts']
    for v in verts:
        base = V((v.co.x * a, v.co.y * b, v.co.z * cz))
        v.co = shape(base) + c
    bm.normal_update()
    faces = list({f for v in verts for f in v.link_faces})
    # material zones by face centroid ---------------------------------------------------------------
    mz = LM['mouth_z']
    for f in faces:
        f.smooth = True
        cen = f.calc_center_median() - c
        f.material_index = 0
        if cen.y < -0.5 * b:
            if abs(cen.x) < 0.030 and (mz - 0.0145 * h) < cen.z < (mz + 0.0150 * h):
                f.material_index = 1
            if abs(cen.x) < 0.024 and abs(cen.z - mz) < 0.0016 * h:
                f.material_index = 2
    for v in verts:
        for bn, w in {"head": 1.0}.items():
            v[mb.dvl][mb._gidx(bn)] = w

    bm.verts.index_update()
    bm.faces.index_update()
    head_faces = {f.index for f in faces}
    # ---- ears
    ear_y = c.y + 0.012
    for sg in (-1, 1):
        mb.add_sphere((sg * (a * 0.995), ear_y, c.z - 0.004 * h), (0.0075, 0.0165 * h, 0.0300 * h), 14, 10, mat=skin,
                      bind=WeightSpec.rigid("head"), rot=Euler((0, 0, sg * 0.30)))
        mb.add_sphere((sg * (a * 0.995 + 0.003), ear_y + 0.004, c.z - 0.002 * h), (0.0050, 0.0110 * h, 0.0220 * h), 12, 8,
                      mat=skin, bind=WeightSpec.rigid("head"), rot=Euler((0, 0, sg * 0.30)))

    info = dict(head_faces=head_faces, center=c, a=a, b=b, cz=cz, h=h, LM=LM, eye_x=eye_x, shape=shape, k=k, verts=[(v.co.copy(), v.normal.copy()) for v in verts])
    return mb, info


def head_surface_y(info, x: float, z: float) -> float:
    """y of the deformed face surface at (x, z) world coordinates (front)."""
    c, a, b, cz, shape = info["center"], info["a"], info["b"], info["cz"], info["shape"]
    X = max(-0.98, min(0.98, (x - c.x) / a))
    Z = max(-0.98, min(0.98, (z - c.z) / cz))
    rad = max(0.0, 1 - X * X - Z * Z)
    p = V((X * a, -b * math.sqrt(rad), Z * cz))
    return (shape(p) + c).y


def build_eyes(spec: Dict, info, L, col, female: bool) -> MeshBuilder:
    mb = MeshBuilder(f"{spec['name']}_Eyes")
    sclera, iris, pupil = L['sclera'], L['iris'], L['pupil']
    mb.slot(sclera), mb.slot(iris), mb.slot(pupil)
    c, eye_x, LM = info["center"], info["eye_x"], info["LM"]
    r = 0.0118 * (0.97 if female else 1.0)
    for sg in (-1, 1):
        x = sg * eye_x
        z = c.z + LM['eye_z']
        y = head_surface_y(info, x, z) + r * 0.72
        n0 = mb.nverts()
        mb.add_sphere((x, y, z), (r, r, r), 24, 16, mat=sclera, bind=WeightSpec.rigid("head"))
        # iris / pupil by angle from the -Y pole
        for f in list(mb.bm.faces)[-(24 * 16):]:
            cen = f.calc_center_median() - V((x, y, z))
            ang = math.acos(max(-1, min(1, -cen.y / max(cen.length, 1e-9))))
            if ang < math.radians(21):
                f.material_index = 1
                if ang < math.radians(8.5):
                    f.material_index = 2
        # iris bulge (cornea) – push the front verts slightly
        for v in mb.verts_from(n0):
            rel = v.co - V((x, y, z))
            ang = math.acos(max(-1, min(1, -rel.y / max(rel.length, 1e-9))))
            if ang < math.radians(24):
                v.co += V((0, -1, 0)) * 0.0012 * (1 - ang / math.radians(24))
    return mb


def build_brows(spec: Dict, info, L, col, female: bool) -> MeshBuilder:
    mb = MeshBuilder(f"{spec['name']}_Brows")
    hair = L['hair_female' if female else 'beard']
    c, eye_x, LM = info["center"], info["eye_x"], info["LM"]
    thick = 0.0045 if female else 0.0070
    for sg in (-1, 1):
        pts = []
        for i in range(8):
            t = i / 7
            x = sg * (eye_x * 0.40 + t * eye_x * 1.30)
            arch = (0.0105 * math.sin(t * math.pi * 0.85) if female else 0.0060 * math.sin(t * math.pi * 0.7))
            z = c.z + LM['brow_z'] + 0.001 + arch - (0.0 if female else 0.0035) * t * t
            y = head_surface_y(info, x, z) - 0.0012
            pts.append(V((x, y, z)))
        rad = [thick * (1.0 - 0.55 * (i / 7) ** 1.6) for i in range(8)]
        mb.add_tube_path(pts, rad, 6, mat=hair, bind=WeightSpec.rigid("head"), squash=0.55, ref=V((0, 0, 1)))
    return mb


# ====================================================================================== hair / beard
def _scalp_samples(info, predicate):
    c = info["center"]
    out = []
    for co, nrm in info["verts"]:
        rel = co - c
        if predicate(rel, nrm):
            out.append((co, nrm))
    return out


def build_beard_from_bm(spec: Dict, head_bm: bmesh.types.BMesh, info, L, seed: int) -> MeshBuilder:
    mb = MeshBuilder(f"{spec['name']}_Beard")
    beard = L['beard']
    c, h, LM = info["center"], info["h"], info["LM"]
    mz = LM['mouth_z']
    rs = rng(seed, "beard")

    def softmask(rel: V) -> float:
        x, y, z = rel
        ax = abs(x)
        if y > 0.020:
            return 0.0
        below_lip = smoothstep(mz - 0.010 * h, mz - 0.024 * h, z)
        cheek_line = (LM['eye_z'] - 0.056 * h) + 0.034 * h * smoothstep(0.03, 0.078, ax)
        cheek = smoothstep(cheek_line + 0.014 * h, cheek_line - 0.004 * h, z) * smoothstep(0.028, 0.046, ax)
        m = max(below_lip, cheek)
        lips = smoothstep(0.037, 0.027, ax) * smoothstep(0.019 * h, 0.011 * h, abs(z - mz))
        return max(0.0, min(1.0, m * (1.0 - lips)))

    vmap, sm, pending, faces_out = {}, {}, [], []
    for v in head_bm.verts:
        sm[v.index] = softmask(v.co - c)
    for f in head_bm.faces:
        if f.material_index != 0 or f.index not in info["head_faces"]:
            continue
        avg = max(sm[v.index] for v in f.verts)
        if avg < 0.18:
            continue
        nv = []
        for v in f.verts:
            if v.index not in vmap:
                s = sm[v.index]
                off = (0.0070 + 0.0020 * mnoise(v.co * 90.0)) * s
                vmap[v.index] = len(pending)
                pending.append(v.co + v.normal * off)
            nv.append(vmap[v.index])
        faces_out.append(nv)
    if pending:
        mb.add_mesh_data(pending, faces_out, mat=beard, bind=WeightSpec.rigid("head"))
        mb.recalc_normals()
    # moustache
    for sg in (-1, 1):
        pts = []
        for i in range(7):
            t = i / 6
            x = sg * (0.003 + t * 0.030)
            z = c.z + mz + 0.0185 * h - t * 0.012 * h - 0.0 * t
            y = None
            pts.append((x, z))
        P = []
        for x, z in pts:
            P.append(V((x, head_surface_y(info, x, z) - 0.003, z)))
        rad = [0.0060 * (1 - 0.35 * (i / 6)) for i in range(7)]
        mb.add_tube_path(P, rad, 7, mat=beard, bind=WeightSpec.rigid("head"), squash=0.75, ref=V((0, 0, 1)))
    return mb


def _hair_clump(mb, p0: V, direction: V, length: float, radius: float, droop: float, mat, bind, rs, segs=6, curl=0.0):
    pts = [p0]
    d = direction.normalized()
    seg = length / 3.0
    p = p0
    for i in range(3):
        d = (d + V((rs.uniform(-curl, curl), rs.uniform(-curl, curl), -droop * (i + 1) * 0.35))).normalized()
        p = p + d * seg
        pts.append(p)
    rad = [radius, radius * 0.9, radius * 0.6, radius * 0.12]
    mb.add_tube_path(pts, rad, segs, mat=mat, bind=bind, squash=0.6, ref=V((0, 0, 1)), caps=True)


def build_hair_male(spec: Dict, head_bm, info, L, seed: int) -> MeshBuilder:
    mb = MeshBuilder(f"{spec['name']}_Hair")
    mat = L['hair_male']
    rs = rng(seed, "hair_m")
    c, h = info["center"], info["h"]
    bind = WeightSpec.rigid("head")

    def mask(rel: V) -> float:
        x, y, z = rel
        front = y < -0.02
        hairline = (0.060 * h + 0.010 * h * smoothstep(0.0, 0.06, abs(x))) if front else (0.004 * h - 0.020 * h * smoothstep(0.0, 0.08, y))
        side = 0.020 * h if abs(x) > 0.05 else 0.0
        s = smoothstep(hairline - 0.006, hairline + 0.006, z - side * 0)
        if abs(x) > 0.060 and z < 0.020 * h:
            s = 0.0          # keep ears free
        if y > 0.02 and z < -0.040 * h:
            s = 0.0
        return s

    sm = {v.index: mask(v.co - c) for v in head_bm.verts}
    vmap, P, F = {}, [], []
    for f in head_bm.faces:
        if f.material_index != 0 or f.index not in info["head_faces"]:
            continue
        avg = sum(sm[v.index] for v in f.verts) / len(f.verts)
        if avg < 0.5:
            continue
        ids = []
        for v in f.verts:
            if v.index not in vmap:
                vmap[v.index] = len(P)
                P.append(v.co + v.normal * (0.0050 + 0.0035 * sm[v.index] + 0.0015 * mnoise(v.co * 60.0)))
            ids.append(vmap[v.index])
        F.append(ids)
    mb.add_mesh_data(P, F, mat=mat, bind=bind)
    mb.recalc_normals()
    # clumps ------------------------------------------------------------------------------------------
    cand = [(v.co.copy(), v.normal.copy()) for v in head_bm.verts if sm[v.index] > 0.9]
    rs.shuffle(cand)
    for co, nrm in cand[:200]:
        rel = co - c
        front = rel.y < -0.045
        top = rel.z > 0.060 * h
        if front:
            dirv = V((rs.uniform(-0.6, 0.2), -0.55, -0.20)) + nrm * 0.25
            ln = rs.uniform(0.030, 0.050)
            droop = 1.2
        elif top:
            dirv = nrm * 0.45 + V((rs.uniform(-0.45, 0.45), rs.uniform(-0.45, 0.25), 0.55))
            ln = rs.uniform(0.024, 0.042)
            droop = 0.8
        else:
            dirv = nrm * 0.55 + V((0, 0, -0.35))
            ln = rs.uniform(0.012, 0.024)
            droop = 0.4
        _hair_clump(mb, co + nrm * 0.003, dirv, ln, rs.uniform(0.0095, 0.0140), droop, mat, bind, rs, 6, 0.18)
    return mb


def build_hair_female(spec: Dict, head_bm, info, L, T, seed: int) -> Tuple[MeshBuilder, MeshBuilder]:
    """Scalp hair (rigid to head) and a long ponytail rigged to pony_1..4."""
    mat = L['hair_female']
    rs = rng(seed, "hair_f")
    c, h, k = info["center"], info["h"], spec["scale"]
    scalp = MeshBuilder(f"{spec['name']}_Hair")
    bind = WeightSpec.rigid("head")

    def mask(rel: V) -> float:
        x, y, z = rel
        front = y < -0.02
        hairline = (0.062 * h + 0.004 * h * smoothstep(0.0, 0.05, abs(x))) if front else (0.000 - 0.030 * h * smoothstep(0.0, 0.08, y))
        s = smoothstep(hairline - 0.005, hairline + 0.005, z)
        if abs(x) > 0.060 and z < 0.006 * h and y > -0.03:
            s = 0.0
        return s

    sm = {v.index: mask(v.co - c) for v in head_bm.verts}
    vmap, P, F = {}, [], []
    for f in head_bm.faces:
        if f.material_index != 0 or f.index not in info["head_faces"]:
            continue
        avg = max(sm[v.index] for v in f.verts)
        if avg < 0.25:
            continue
        ids = []
        for v in f.verts:
            if v.index not in vmap:
                vmap[v.index] = len(P)
                P.append(v.co + v.normal * ((0.0085 + 0.0010 * mnoise(v.co * 50.0)) * (0.35 + 0.65 * sm[v.index])))
            ids.append(vmap[v.index])
        F.append(ids)
    scalp.add_mesh_data(P, F, mat=mat, bind=bind)
    scalp.recalc_normals()
    # swept-back strands over the scalp (direction towards ponytail root)
    root = V((0, 0.095 * k, 1.735 * k))
    cand = [(v.co.copy(), v.normal.copy()) for v in head_bm.verts if sm[v.index] > 0.9]
    rs.shuffle(cand)
    for co, nrm in cand[:260]:
        to_root = (root - co)
        dirv = (to_root.normalized() * 0.8 + nrm * 0.25)
        _hair_clump(scalp, co + nrm * 0.004, dirv, rs.uniform(0.030, 0.050), rs.uniform(0.0035, 0.0055), 0.1, mat, bind, rs, 5, 0.04)
    # --- ponytail ---------------------------------------------------------------------------------------
    pt = MeshBuilder(f"{spec['name']}_Ponytail")
    pony_bones = ["pony_1", "pony_2", "pony_3", "pony_4", "head"]
    pb = WeightSpec.auto(pony_bones, T, 4.0)
    chain = [T["pony_1"]["head"]] + [T[f"pony_{i}"]["tail"] for i in range(1, 5)]
    # dense interpolated centre line
    cl, rad = [], []
    for i in range(len(chain) - 1):
        for j in range(5):
            cl.append(chain[i].lerp(chain[i + 1], j / 5))
    cl.append(chain[-1])
    n = len(cl)
    for i in range(n):
        t = i / (n - 1)
        rad.append(0.040 * k * (1.0 + 0.55 * math.sin(min(1, t * 2.4) * 1.7)) * (1.0 - 0.80 * t ** 2.2) + 0.003)
    pt.add_tube_path(cl, rad, 14, mat=mat, bind=pb, squash=0.85, ref=V((1, 0, 0)))
    for si in range(70):                          # individual strands for silhouette
        off = V((rs.uniform(-0.022, 0.022) * k, rs.uniform(-0.012, 0.016) * k, 0))
        ph = rs.uniform(0, 6.28)
        pts, rr = [], []
        for i in range(n):
            t = i / (n - 1)
            wob = V((math.sin(t * 5 + ph) * 0.006 * k * t, math.cos(t * 4 + ph) * 0.005 * k * t, 0))
            pts.append(cl[i] + off * (0.6 + 0.9 * t) + wob)
            rr.append(rs.uniform(0.0060, 0.0095) * (1.0 - 0.9 * t ** 2.0) + 0.0006)
        pt.add_tube_path(pts, rr, 5, mat=mat, bind=pb, squash=0.7, ref=V((1, 0, 0)))
    # hair tie
    r0 = chain[0]
    pt.add_cyl(r0 + V((0, 0.0, -0.008)), r0 + V((0, 0.012 * k, -0.034 * k)), 0.036 * k, 0.034 * k, 14, mat=L['hair_tie'],
               bind=WeightSpec.rigid("pony_1"))
    return scalp, pt
