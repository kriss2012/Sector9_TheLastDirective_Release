"""Hard-surface weapon models: handgun, machine-gun (carbine) and kukri.

Conventions (all weapons): origin = main grip centre, barrel / blade points to -Y, up = +Z.
Each weapon is a hierarchy:  ``WPN_<Name>`` (empty root) -> mesh parts + ``ATT_*`` attachment empties.
Moving parts (slide, bolt, magazine, charging handle, trigger) are separate objects with pivots at
their natural hinge/slide origin so they can be animated (see ``animate_weapon_parts``).

Dimensions are derived from the supplied reference images: the carbine from the multi-view sheet
(tan receiver, black slotted handguard, holographic sight, vertical grip, A-frame front sight,
slotted flash hider, collapsible stock); the kukri from its sheet (fullered blade with cho notch,
ebony diamond-checkered grip, brass-rimmed pommel, leather sheath with brass chape, karda+chakmak).
The handgun is modelled after the compact two-tone pistol visible in the character sheet
("Action Pose 1"); no dedicated handgun reference was supplied, so details are generic.
"""
from __future__ import annotations
import math
from typing import Dict, List, Optional, Sequence, Tuple

import bpy
import bmesh
from mathutils import Vector, Euler, Matrix

from .utils import (MeshBuilder, V, add_bevel, apply_modifiers, get_collection, new_empty, ring_ellipse,
                    smoothstep, gauss, frame_from_tangent, link_only, BuildError)


# --------------------------------------------------------------------------------------- helpers
def _box(mb: MeshBuilder, c, s, mat, rot=None, bevel=0.0, taper=None):
    mb.add_box(c, s, rot=rot, mat=mat, bevel=bevel, taper=taper)


def _translate(mb: MeshBuilder, off: Vector) -> None:
    bmesh.ops.translate(mb.bm, vec=-V(off), verts=list(mb.bm.verts))


def _finish(mb: MeshBuilder, col, root, origin=(0, 0, 0), bevel: float = 0.0006) -> bpy.types.Object:
    """Re-origin to `origin`, create the object, parent under root, bevel edges."""
    if any(abs(a) > 0 for a in origin):
        _translate(mb, V(origin))
    mb.recalc_normals()
    ob = mb.to_object(col, loc=origin)
    ob.parent = root
    if bevel > 0 and len(ob.data.polygons) < 20000:
        try:
            add_bevel(ob, width=bevel, segments=2, angle_deg=40)
        except Exception as exc:  # bevel is cosmetic
            print(f"[weapons] bevel skipped on {ob.name}: {exc}")
    for p in ob.data.polygons:
        p.use_smooth = True
    return ob


def _bool_cut(target: bpy.types.Object, cutter_mb: MeshBuilder, col, origin=(0, 0, 0)) -> None:
    """Boolean difference using a temporary cutter object (EXACT solver)."""
    cutter_mb.recalc_normals()
    cut = cutter_mb.to_object(col, loc=(0, 0, 0))
    mod = target.modifiers.new("Cut", 'BOOLEAN')
    mod.object = cut
    mod.operation = 'DIFFERENCE'
    mod.solver = 'EXACT'
    try:
        mod.use_self = True
    except Exception:
        pass
    apply_modifiers(target)
    bpy.data.objects.remove(cut, do_unlink=True)


def _root(name: str, col) -> bpy.types.Object:
    r = new_empty(name, col, display='PLAIN_AXES', size=0.05)
    return r


def _att(name: str, col, parent, loc, rot=(0, 0, 0), size=0.02) -> bpy.types.Object:
    e = new_empty(name, col, loc=loc, display='ARROWS', size=size)
    e.rotation_euler = Euler(rot)
    e.parent = parent
    return e


# =========================================================================================
# PISTOL
# =========================================================================================
def build_pistol(L, col) -> Dict[str, object]:
    root = _root("WPN_Handgun", col)
    parts: Dict[str, bpy.types.Object] = {}
    tan, poly, gm, steel = L['cerakote_tan'], L['polymer'], L['gunmetal'], L['steel_bare']
    alpha = math.radians(17.0)           # grip rake: bottom toward +Y
    R = Euler((alpha, 0, 0))

    # ---------------- slide (separate: recoils on fire)
    sl = MeshBuilder("Handgun_Slide")
    _box(sl, (0, -0.009, 0.074), (0.028, 0.158, 0.030), tan, bevel=0.0035, taper=(0.82, 1.0))
    _box(sl, (0, -0.088, 0.071), (0.020, 0.012, 0.022), tan, bevel=0.003, taper=(0.8, 1.0))   # muzzle nose
    sl.add_cyl((0, -0.090, 0.071), (0, -0.096, 0.071), 0.0062, 0.0062, 14, mat=gm)             # barrel crown
    for sg in (+1, -1):
        for i in range(6):                                                                        # rear serrations
            y = 0.036 + i * 0.0045
            _box(sl, (sg * 0.0141, y, 0.074), (0.0014, 0.0017, 0.020), gm)
        _box(sl, (sg * 0.0142, 0.000, 0.0785), (0.0010, 0.034, 0.0105), gm)                      # ejection port
    _box(sl, (0, -0.079, 0.0912), (0.0040, 0.007, 0.0065), gm)                                    # front sight
    _box(sl, (+0.0065, 0.064, 0.0905), (0.0045, 0.008, 0.0065), gm)                                # rear sight (2 posts)
    _box(sl, (-0.0065, 0.064, 0.0905), (0.0045, 0.008, 0.0065), gm)
    _box(sl, (0, -0.084, 0.0595), (0.012, 0.010, 0.004), steel)                                   # guide rod seat
    parts['slide'] = _finish(sl, col, root, origin=(0, 0.0, 0.074), bevel=0.0004)

    # ---------------- frame + grip (static body)
    fr = MeshBuilder("Handgun_Frame")
    _box(fr, (0, -0.040, 0.049), (0.025, 0.093, 0.020), poly, bevel=0.0025)                       # dust cover
    _box(fr, (0, 0.030, 0.052), (0.027, 0.080, 0.016), poly, bevel=0.0025)                        # frame under slide
    for sg in (+1, -1):                                                                             # rail slots
        for y in (-0.050, -0.040):
            _box(fr, (sg * 0.0127, y, 0.0395), (0.0012, 0.0045, 0.0070), gm)
    top = V((0, 0.046, 0.046))
    gl = 0.112
    gc = top + R.to_matrix() @ V((0, 0, -gl / 2))
    _box(fr, gc, (0.033, 0.045, gl), poly, rot=R, bevel=0.0035)                                    # grip
    bc = top + R.to_matrix() @ V((0, 0.003, -gl + 0.003))
    _box(fr, bc, (0.037, 0.050, 0.014), poly, rot=R, bevel=0.003)                                  # magwell flare
    _box(fr, (0, 0.077, 0.050), (0.026, 0.014, 0.012), poly, bevel=0.003)                         # beavertail
    for sg in (+1, -1):                                                                             # side panel texture plates
        for k in range(3):
            pc = top + R.to_matrix() @ V((sg * 0.0168, 0.0, -0.030 - k * 0.026))
            _box(fr, pc, (0.0012, 0.034, 0.020), gm, rot=R)
    # trigger guard (boxes forming a rounded rectangle)
    _box(fr, (0, -0.030, 0.032), (0.0095, 0.0055, 0.030), poly, bevel=0.0018)
    _box(fr, (0, -0.011, 0.0185), (0.0095, 0.040, 0.0055), poly, bevel=0.0018)
    _box(fr, (0, 0.007, 0.030), (0.0095, 0.0055, 0.028), poly, bevel=0.0018)
    for sg in (+1, -1):                                                                             # slide stop / takedown
        _box(fr, (sg * 0.0142, 0.012, 0.0505), (0.0030, 0.020, 0.0040), gm)
    _box(fr, (0.0145, 0.040, 0.048), (0.003, 0.010, 0.0055), gm)                                  # mag release
    parts['frame'] = _finish(fr, col, root, bevel=0.0005)

    # ---------------- trigger (pivot at top)
    tr = MeshBuilder("Handgun_Trigger")
    _box(tr, (0, -0.0075, 0.030), (0.0060, 0.0050, 0.020), gm, bevel=0.0008)
    _box(tr, (0, -0.0110, 0.0225), (0.0060, 0.0100, 0.0040), gm, bevel=0.0008)
    parts['trigger'] = _finish(tr, col, root, origin=(0, -0.0075, 0.042), bevel=0.0)

    # ---------------- magazine (separate; slides down)
    mg = MeshBuilder("Handgun_Magazine")
    mc = top + R.to_matrix() @ V((0, 0.0005, -0.050))
    _box(mg, mc, (0.0255, 0.0370, 0.100), gm, rot=R, bevel=0.0015)
    bp = top + R.to_matrix() @ V((0, 0.004, -gl - 0.002))
    _box(mg, bp, (0.0345, 0.0490, 0.009), poly, rot=R, bevel=0.0018)
    parts['magazine'] = _finish(mg, col, root, origin=tuple(top + R.to_matrix() @ V((0, 0, -0.002))), bevel=0.0)

    # ---------------- attachment points
    _att("ATT_Grip_R", col, root, (0, 0.030, 0.000), size=0.03)
    _att("ATT_Support_L", col, root, (0.012, 0.035, -0.040), size=0.02)
    _att("ATT_Muzzle", col, root, (0, -0.098, 0.071), size=0.02)
    _att("ATT_Eject", col, root, (-0.014, 0.0, 0.080), size=0.02)
    _att("ATT_Holster", col, root, (0, 0.0, 0.05), size=0.02)
    return dict(root=root, parts=parts, name="Handgun")


# =========================================================================================
# CARBINE / "MACHINE GUN"
# =========================================================================================
def build_rifle(L, col) -> Dict[str, object]:
    root = _root("WPN_MachineGun", col)
    parts: Dict[str, bpy.types.Object] = {}
    tan, poly, gm, steel = L['cerakote_tan'], L['polymer'], L['gunmetal'], L['steel_bare']
    glass, reticle, red = L['glass_lens'], L['reticle'], L['badge_red']
    BZ = 0.065        # bore axis height

    # ---------------------------------------------------------------- body (receivers, stock, grips)
    B = MeshBuilder("MG_Body")
    # receivers
    _box(B, (0, -0.0135, 0.0675), (0.046, 0.180, 0.056), tan, bevel=0.0030)                        # upper receiver
    _box(B, (0, -0.0120, 0.0190), (0.044, 0.172, 0.044), tan, bevel=0.0030)                        # lower receiver
    _box(B, (0, -0.0685, -0.0100), (0.041, 0.052, 0.034), tan, bevel=0.0030)                       # mag well
    _box(B, (0, 0.066, 0.040), (0.043, 0.032, 0.050), tan, bevel=0.0030)                           # rear block
    for sg in (+1, -1):
        _box(B, (sg * 0.0232, 0.003, 0.0690), (0.0012, 0.050, 0.024), gm)                          # ejection port
        _box(B, (sg * 0.0229, -0.0415, 0.0650), (0.0010, 0.032, 0.030), gm)                        # fwd assist panel
        _box(B, (sg * 0.0229, 0.025, 0.0420), (0.0010, 0.100, 0.0030), gm)                         # split line
        for i in range(3):
            _box(B, (sg * 0.0226, 0.020 + i * 0.012, 0.0560), (0.0010, 0.0070, 0.020), gm)         # dust-cover ridges
    # fire controls
    for sg in (+1, -1):
        B.add_cyl((sg * 0.0222, 0.040, 0.0225), (sg * 0.0268, 0.040, 0.0225), 0.0062, 0.0062, 14, mat=gm)   # selector hub
        _box(B, (sg * 0.0290, 0.040, 0.0245), (0.0030, 0.0220, 0.0060), gm, rot=Euler((0, 0, 0.5)))       # selector lever
        B.add_cyl((sg * 0.0222, -0.050, 0.014), (sg * 0.0258, -0.050, 0.014), 0.0050, 0.0050, 12, mat=gm)  # mag catch
    _box(B, (0.0235, 0.012, 0.034), (0.0020, 0.0140, 0.0080), gm)                                           # bolt release
    for (yy, zz) in ((0.050, 0.041), (0.037, 0.0415)):                                                      # reference red dots
        B.add_cyl((0.0224, yy, zz), (0.0238, yy, zz), 0.0027, 0.0027, 12, mat=red)
    # trigger guard
    B.add_tube_path([V((0.0, 0.012, -0.0030)), V((0, 0.003, -0.0140)), V((0, -0.020, -0.0165)), V((0, -0.040, -0.0110)),
                     V((0, -0.044, 0.0000))], [0.0045] * 5, 8, mat=gm, squash=1.0, caps=True)
    # top rail teeth
    _box(B, (0, -0.0135, 0.0962), (0.0210, 0.176, 0.0030), gm, bevel=0.0006)
    for i in range(26):
        y = 0.071 - i * 0.0068
        _box(B, (0, y, 0.0990), (0.0215, 0.0036, 0.0030), gm)
    _box(B, (0, -0.1665, 0.1020), (0.0215, 0.1200, 0.0035), gm)                                  # handguard top rail
    for i in range(16):
        _box(B, (0, -0.1090 - i * 0.0075, 0.1045), (0.0220, 0.0038, 0.0030), gm)
    # pistol grip (raked back 29 deg) -------------------------------------------------------
    a = math.radians(29)
    R = Euler((a, 0, 0))
    top = V((0, 0.032, 0.021))
    gl = 0.100
    gc = top + R.to_matrix() @ V((0, 0, -gl / 2))
    _box(B, gc, (0.037, 0.042, gl), poly, rot=R, bevel=0.0045, taper=(0.95, 0.95))
    for k in range(4):                                                                       # finger grooves / texture bands
        pc = top + R.to_matrix() @ V((0, -0.0185, -0.020 - k * 0.020))
        B.add_cyl(pc + V((-0.0150, 0, 0)), pc + V((0.0150, 0, 0)), 0.0065, 0.0065, 10, mat=gm)
    _box(B, top + R.to_matrix() @ V((0, 0.0, -gl - 0.002)), (0.040, 0.046, 0.008), poly, rot=R, bevel=0.003)
    # ---------------------------------------------------------------- buffer tube + collapsible stock
    B.add_cyl((0, 0.070, 0.063), (0, 0.258, 0.063), 0.0195, 0.0195, 20, mat=poly)
    for i in range(14):                                                                      # tube ribs
        y = 0.095 + i * 0.0105
        B.add_cyl((0, y, 0.063), (0, y + 0.0045, 0.063), 0.0215, 0.0215, 20, mat=poly)
    _box(B, (0, 0.1850, 0.0825), (0.040, 0.150, 0.018), poly, bevel=0.0045, taper=(0.9, 1.0))  # cheek riser
    _box(B, (0, 0.262, 0.026), (0.046, 0.026, 0.112), poly, bevel=0.0055)                    # butt plate
    for i in range(4):                                                                       # butt plate grooves
        _box(B, (0, 0.2760, 0.050 - i * 0.025), (0.040, 0.0018, 0.0035), gm)
    for sg in (+1, -1):                                                                      # diagonal struts
        B.add_cyl((sg * 0.015, 0.250, -0.026), (sg * 0.015, 0.108, 0.034), 0.0072, 0.0072, 10, mat=poly)
        B.add_cyl((sg * 0.015, 0.248, 0.034), (sg * 0.015, 0.215, 0.050), 0.0060, 0.0060, 10, mat=poly)
    _box(B, (0, 0.250, -0.022), (0.038, 0.020, 0.012), poly, bevel=0.0025)                   # strut lower yoke
    _box(B, (0.0, 0.190, 0.0155), (0.012, 0.026, 0.0100), gm, rot=Euler((0.45, 0, 0)))       # adjust lever
    # ---------------------------------------------------------------- front: barrel, gas tube, gas block
    B.add_cyl((0, -0.1000, BZ), (0, -0.3900, BZ), 0.0085, 0.0085, 20, mat=steel)
    B.add_cyl((0, -0.3900, BZ), (0, -0.4730, BZ), 0.0095, 0.0095, 20, mat=gm)               # muzzle step
    B.add_cyl((0, -0.2200, 0.0865), (0, -0.3750, 0.0865), 0.0052, 0.0052, 14, mat=steel)    # gas tube
    _box(B, (0, -0.2630, 0.0620), (0.036, 0.046, 0.044), gm, bevel=0.0030)                 # bracket block
    _box(B, (0, -0.2630, 0.0860), (0.026, 0.044, 0.006), gm)                                # rail bridge
    for sg in (+1, -1):
        _box(B, (sg * 0.0185, -0.2630, 0.0620), (0.0012, 0.030, 0.026), steel)             # side window plates
        B.add_cyl((sg * 0.0182, -0.2800, 0.0480), (sg * 0.0212, -0.2800, 0.0480), 0.0045, 0.0045, 12, mat=steel)  # screws
    # front sight (A-frame) ----------------------------------------------------------------
    B.add_cyl((0, -0.3510, BZ), (0, -0.3820, BZ), 0.0135, 0.0135, 18, mat=steel)
    for sg in (+1, -1):
        B.add_tube_path([V((sg * 0.0030, -0.3560, 0.0770)), V((sg * 0.0030, -0.3640, 0.1200))], [0.0040, 0.0032], 8, mat=steel)
        B.add_tube_path([V((sg * 0.0030, -0.3780, 0.0770)), V((sg * 0.0030, -0.3690, 0.1200))], [0.0040, 0.0032], 8, mat=steel)
        _box(B, (sg * 0.0085, -0.3660, 0.1190), (0.0040, 0.0100, 0.016), steel, bevel=0.0008)   # sight ears
    _box(B, (0, -0.3660, 0.1240), (0.0030, 0.0120, 0.0140), steel, bevel=0.0008)              # sight post
    # vertical foregrip ---------------------------------------------------------------------
    _box(B, (0, -0.2620, 0.0330), (0.030, 0.034, 0.014), gm, bevel=0.0020)                  # grip mount
    fg_top, fg_bot = V((0, -0.2620, 0.028)), V((0, -0.2560, -0.055))
    B.add_cyl(fg_top, fg_bot, 0.0165, 0.0175, 16, mat=poly, squash=0.95)
    for k in range(5):                                                                        # finger grooves
        t = 0.12 + 0.17 * k
        p = fg_top.lerp(fg_bot, t)
        B.add_cyl(p, p + V((0, 0.0, -0.0080)), 0.0188, 0.0188, 16, mat=poly, squash=0.95)
    B.add_cyl(fg_bot, fg_bot + V((0, 0.0, -0.007)), 0.0210, 0.0200, 16, mat=poly)           # flared base
    B.add_cyl(fg_bot + V((0, 0, -0.007)), fg_bot + V((0, 0, -0.0085)), 0.0100, 0.0100, 12, mat=gm)   # base cap
    parts['body'] = _finish(B, col, root, bevel=0.0005)

    # ---------------------------------------------------------------- handguard (boolean-slotted)
    H = MeshBuilder("MG_Handguard")
    _box(H, (0, -0.1665, 0.0630), (0.054, 0.1260, 0.074), poly, bevel=0.0050, taper=(0.82, 1.0))
    H.recalc_normals()
    hg = H.to_object(col)
    hg.parent = root
    C = MeshBuilder("cutter")
    for k in range(7):                                                                         # oval vents, both sides
        y = -0.1140 - k * 0.0160
        for sg in (+1, -1):
            C.add_sphere((sg * 0.0265, y, 0.0780), (0.0090, 0.0100, 0.0050), 14, 8, mat=poly)
    for z in (0.0450, 0.0520, 0.0590):                                                          # long engraved grooves
        for sg in (+1, -1):
            C.add_box((sg * 0.0268, -0.1665, z), (0.0060, 0.1000, 0.0022), mat=poly)
    try:
        _bool_cut(hg, C, col)
    except Exception as exc:
        print(f"[weapons] handguard boolean failed ({exc}); continuing with uncut handguard")
    for p in hg.data.polygons:
        p.use_smooth = True
    try:
        add_bevel(hg, width=0.0004, segments=1, angle_deg=40)
    except Exception:
        pass
    parts['handguard'] = hg

    # ---------------------------------------------------------------- flash hider (slotted)
    FH = MeshBuilder("MG_FlashHider")
    FH.add_cyl((0, -0.4730, BZ), (0, -0.5400, BZ), 0.0140, 0.0140, 24, mat=gm)
    FH.add_cyl((0, -0.4730, BZ), (0, -0.4800, BZ), 0.0155, 0.0155, 24, mat=gm)
    FH.add_cyl((0, -0.5340, BZ), (0, -0.5400, BZ), 0.0155, 0.0155, 24, mat=gm)
    FH.recalc_normals()
    fh = FH.to_object(col)
    fh.parent = root
    C2 = MeshBuilder("cutter2")
    for ang in (0, 90, 180, 270):
        c, s = math.cos(math.radians(ang)), math.sin(math.radians(ang))
        C2.add_box((c * 0.0140, -0.5190, BZ + s * 0.0140), (0.0055 if s == 0 else 0.030, 0.0300, 0.030 if s == 0 else 0.0055), mat=gm)
    try:
        _bool_cut(fh, C2, col)
    except Exception as exc:
        print(f"[weapons] flash hider boolean failed ({exc})")
    # bore hole
    parts['flash_hider'] = fh

    # ---------------------------------------------------------------- bolt (visible in port; recoils)
    BO = MeshBuilder("MG_Bolt")
    _box(BO, (0, 0.000, 0.0690), (0.0200, 0.0300, 0.0140), steel, bevel=0.0010)
    _box(BO, (0.0090, 0.000, 0.0745), (0.0040, 0.0220, 0.0050), gm)
    parts['bolt'] = _finish(BO, col, root, origin=(0, 0.0, 0.0690), bevel=0.0)

    # ---------------------------------------------------------------- charging handle
    CH = MeshBuilder("MG_ChargingHandle")
    _box(CH, (0, 0.082, 0.0885), (0.010, 0.020, 0.0100), gm, bevel=0.0010)
    for sg in (+1, -1):
        _box(CH, (sg * 0.0165, 0.088, 0.0885), (0.0200, 0.0120, 0.0090), gm, bevel=0.0012)
    parts['charging_handle'] = _finish(CH, col, root, origin=(0, 0.082, 0.0885), bevel=0.0)

    # ---------------------------------------------------------------- magazine (separate, curved, ribbed)
    M = MeshBuilder("MG_Magazine")
    path = [V((0, -0.0670, 0.020)), V((0, -0.0725, -0.015)), V((0, -0.0830, -0.050)), V((0, -0.0950, -0.095))]
    widths = [0.0125, 0.0125, 0.0128, 0.0130]
    depths = [0.0200, 0.0215, 0.0235, 0.0250]
    rings = []
    for i, p in enumerate(path):
        tan_v = (path[min(i + 1, 3)] - path[max(i - 1, 0)]).normalized()
        _, u, v = frame_from_tangent(tan_v, V((1, 0, 0)))
        rings.append(ring_ellipse(p, u, v, widths[i], depths[i], 20, power=5.0))
    M.add_loft(rings, caps=True, mat=poly)
    for k in range(5):                                                                        # window grid ribs
        t = (k + 0.7) / 5.4
        i = min(2, int(t * 3))
        p = path[0].lerp(path[3], t)
        for sg in (+1, -1):
            _box(M, (sg * 0.0134, p.y, p.z), (0.0010, 0.034 + 0.003 * t, 0.0050), gm)
    _box(M, (0, path[3].y - 0.0012, path[3].z - 0.0035), (0.0300, 0.0560, 0.0070), poly, bevel=0.002)   # base plate
    parts['magazine'] = _finish(M, col, root, origin=(0, -0.0670, 0.020), bevel=0.0004)

    # ---------------------------------------------------------------- holographic sight (modular)
    S = MeshBuilder("MG_Sight")
    _box(S, (0, 0.000, 0.1085), (0.034, 0.075, 0.0090), gm, bevel=0.0015)                       # mount base
    for sg in (+1, -1):
        _box(S, (sg * 0.0180, 0.000, 0.1160), (0.0050, 0.060, 0.0100), gm, bevel=0.0012)
    _box(S, (0, -0.0070, 0.1370), (0.0450, 0.0750, 0.0300), gm, bevel=0.0040, taper=(0.96, 0.96))   # housing
    _box(S, (0, -0.0070, 0.1545), (0.0430, 0.0720, 0.0050), gm, bevel=0.0025)                   # roof
    S.add_cyl((0, -0.0420, 0.1390), (0, -0.0720, 0.1390), 0.0200, 0.0210, 24, mat=gm, squash=1.0)   # front hood tube
    S.add_cyl((0, -0.0735, 0.1390), (0, -0.0775, 0.1390), 0.0150, 0.0150, 24, mat=glass)    # front lens
    for sg in (+1, -1):                                                                          # rear window frame
        _box(S, (sg * 0.0205, 0.0345, 0.1380), (0.0050, 0.0090, 0.0400), gm, bevel=0.0010)
    _box(S, (0, 0.0345, 0.1575), (0.0460, 0.0090, 0.0060), gm, bevel=0.0012)
    _box(S, (0, 0.0345, 0.1170), (0.0460, 0.0090, 0.0060), gm, bevel=0.0012)
    _box(S, (0, 0.0350, 0.1380), (0.0350, 0.0016, 0.0340), glass)                               # rear glass
    _box(S, (0, 0.0330, 0.1380), (0.0030, 0.0010, 0.0030), reticle)                             # reticle dot
    for sg in (+1, -1):                                                                          # brightness knobs
        S.add_cyl((sg * 0.0225, 0.0100, 0.1280), (sg * 0.0275, 0.0100, 0.1280), 0.0085, 0.0085, 14, mat=steel)
        S.add_cyl((sg * 0.0275, 0.0100, 0.1280), (sg * 0.0285, 0.0100, 0.1280), 0.0060, 0.0060, 12, mat=gm)
    parts['sight'] = _finish(S, col, root, bevel=0.0004)

    # flip-up rear iron sight (folded base visible in the reference)
    RS = MeshBuilder("MG_RearSight")
    _box(RS, (0, 0.0730, 0.1020), (0.016, 0.014, 0.012), gm, bevel=0.0012)
    for sg in (+1, -1):
        _box(RS, (sg * 0.0060, 0.0740, 0.1140), (0.0030, 0.0070, 0.0140), gm, bevel=0.0008)
    parts['rear_sight'] = _finish(RS, col, root, bevel=0.0)

    # ---------------------------------------------------------------- attachment points
    _att("ATT_Grip_R", col, root, (0, 0.050, 0.0), size=0.03)
    _att("ATT_Support_L", col, root, (0, -0.2580, 0.0), size=0.03)                  # left hand on vertical grip
    _att("ATT_Muzzle", col, root, (0, -0.5400, BZ), size=0.02)
    _att("ATT_Sight", col, root, (0.0, 0.0345, 0.1380), size=0.02)
    _att("ATT_Eject", col, root, (-0.0235, 0.0, 0.0690), size=0.02)
    _att("ATT_Sling_Rear", col, root, (0.0, 0.2500, 0.0), size=0.02)
    _att("ATT_Stock", col, root, (0.0, 0.2620, 0.0260), size=0.02)
    return dict(root=root, parts=parts, name="MachineGun")


# =========================================================================================
# KUKRI
# =========================================================================================
def _kukri_profile(t: float, L: float = 0.340) -> Tuple[Vector, Vector, float]:
    """Spine position S(t), unit normal n (edge -> spine) and blade width w(t) in the YZ plane."""
    drop = 0.082
    y0 = -0.085
    S = V((0.0, y0 - L * t, -drop * t * t))
    dY, dZ = -L, -2 * drop * t
    T = V((0, dY, dZ)).normalized()
    n = V((0, T.z, -T.y))                      # for T = -Y  ->  n = +Z
    w0, w1 = 0.037, 0.064
    w = w0 + (w1 - w0) * smoothstep(0.0, 0.62, t)
    if t > 0.70:
        x = (t - 0.70) / 0.30
        w *= math.sqrt(max(0.0, 1.0 - x * x)) ** 1.1
    w *= 1.0 - 0.55 * gauss(t - 0.055, 0.0095)    # cho / kaudi notch at the base of the edge
    return S, n, w


KUKRI_SX = 0.17          # display offset of the sheath along +X (also used to 'sheathe' the blade)


def build_kukri(L, col) -> Dict[str, object]:
    root = _root("WPN_Kukri", col)
    parts: Dict[str, bpy.types.Object] = {}
    blade_m, wood, grip, brass, steel, leather, webbing = (L['blade'], L['wood_dark'], L['grip_diamond'], L['brass'],
                                                           L['steel_bare'], L['leather_black'], L['webbing_olive'])
    # ---------------------------------------------------------------- blade
    Bm = MeshBuilder("Kukri_Blade")
    th_full, th_spine, dep = 0.0034, 0.0030, 0.0017
    fr = [0.00, 0.10, 0.30, 0.52, 0.57, 0.75, 0.80, 1.00]          # d / w stations from the edge to the spine
    NT = 96
    rings = []
    for i in range(NT + 1):
        t = min(0.996, i / NT)
        S, n, w = _kukri_profile(t)
        w = max(w, 0.0012)
        groove = smoothstep(0.02, 0.09, t) * (1.0 - smoothstep(0.56, 0.68, t))
        ths = []
        for f in fr:
            if f == 0.0:
                th = 0.0003
            elif f == 0.10:
                th = 0.0013
            elif f in (0.57, 0.75):
                th = th_full - dep * groove
            elif f == 1.0:
                th = th_spine
            else:
                th = th_full
            if t > 0.9:
                th *= max(0.25, 1.0 - (t - 0.9) * 7.0)
            ths.append(th)
        E = S - n * w
        left = [E + n * (f * w) + V((th, 0, 0)) for f, th in zip(fr[1:], ths[1:])]
        right = [E + n * (f * w) - V((th, 0, 0)) for f, th in zip(fr[1:], ths[1:])]
        ring = [E + V((0, 0, 0))] + left + right[::-1]
        rings.append(ring)
    Bm.add_loft(rings, caps=True, mat=blade_m)
    # tang inside the bolster
    Bm.add_box((0, -0.060, 0.0), (0.0075, 0.050, 0.020), mat=steel)
    parts['blade'] = _finish(Bm, col, root, bevel=0.0)

    # ---------------------------------------------------------------- handle
    Hm = MeshBuilder("Kukri_Handle")
    def hring(y, rx, rz):
        return ring_ellipse(V((0, y, 0)), V((1, 0, 0)), V((0, 0, 1)), rx, rz, 24, power=2.0)
    # bolster (steel collar) with brass band
    Hm.add_loft([hring(-0.0900, 0.0150, 0.0105), hring(-0.0780, 0.0172, 0.0140), hring(-0.0650, 0.0178, 0.0148)],
                caps=True, mat=steel)
    Hm.add_cyl((0, -0.0650, 0), (0, -0.0605, 0), 0.0190, 0.0190, 24, mat=brass, squash=0.84)
    # diamond-checkered grip
    gy = [-0.0600, -0.0450, -0.0250, -0.0050, 0.0050]
    gr = [(0.0172, 0.0150), (0.0180, 0.0156), (0.0186, 0.0160), (0.0184, 0.0158), (0.0178, 0.0153)]
    Hm.add_loft([hring(y, a, b) for y, (a, b) in zip(gy, gr)], caps=False, mat=grip)
    # ridges
    for y in (0.0065, 0.0100):
        Hm.add_cyl((0, y, 0), (0, y + 0.0025, 0), 0.0198, 0.0198, 24, mat=wood, squash=0.86)
    # lower smooth wooden part flaring into pommel
    wy = [0.0130, 0.0250, 0.0380, 0.0490, 0.0580, 0.0650]
    wr = [(0.0186, 0.0160), (0.0192, 0.0165), (0.0200, 0.0172), (0.0230, 0.0198), (0.0290, 0.0245), (0.0350, 0.0290)]
    Hm.add_loft([hring(y, a, b) for y, (a, b) in zip(wy, wr)], caps=False, mat=wood)
    # pommel cap: steel disc with brass rim and rivet
    Hm.add_cyl((0, 0.0650, 0), (0, 0.0690, 0), 0.0365, 0.0365, 28, mat=brass, squash=0.83)
    Hm.add_cyl((0, 0.0690, 0), (0, 0.0705, 0), 0.0330, 0.0330, 28, mat=steel, squash=0.83)
    Hm.add_cyl((0, 0.0705, 0), (0, 0.0740, 0), 0.0070, 0.0058, 14, mat=brass)
    parts['handle'] = _finish(Hm, col, root, bevel=0.0004)

    # ---------------------------------------------------------------- sheath (display layout: offset in +X)
    Sm = MeshBuilder("Kukri_Sheath")
    rings = []
    NS = 48
    sx = KUKRI_SX
    for i in range(NS + 1):
        t = 0.015 + 0.955 * i / NS
        S, n, w = _kukri_profile(t)
        w = max(w, 0.030)
        sw = (w + 0.016) * (1.0 - 0.12 * smoothstep(0.7, 1.0, t))
        c = S - n * (w * 0.5 - 0.002) + V((sx, 0, 0))
        _, u, v = V((0, 0, 0)), V((1, 0, 0)), n
        rx = 0.0205 * (1.0 - 0.45 * smoothstep(0.85, 1.0, t))
        rings.append(ring_ellipse(c, u, v, rx, sw / 2, 22, power=2.6))
    split = int(NS * 0.86)
    Sm.add_loft(rings[: split + 1], caps=True, mat=leather)
    Sm.add_loft(rings[split:], caps=True, mat=brass)                                        # brass chape
    # throat reinforcement + belt frog
    S0, n0, w0 = _kukri_profile(0.02)
    Sm.add_loft([[p + V((0, -0.0005, 0)) for p in ring_ellipse(S0 - n0 * (w0 * 0.5 - 0.002) + V((sx, 0, 0)), V((1, 0, 0)), n0,
                                                               0.0222, (w0 + 0.021) / 2, 22, power=2.6)],
                 [p for p in ring_ellipse(S0 - n0 * (w0 * 0.5 - 0.002) + V((sx, -0.016, 0)), V((1, 0, 0)), n0,
                                          0.0222, (w0 + 0.021) / 2, 22, power=2.6)]], caps=True, mat=leather)
    Sm.add_box((sx - 0.0245, -0.140, 0.006), (0.0045, 0.075, 0.040), mat=webbing)                 # frog strap (back)
    Sm.add_box((sx - 0.0250, -0.118, 0.006), (0.0060, 0.012, 0.046), mat=L['metal_hw'])           # frog buckle
    # pockets for karda / chakmak (front face)
    S1, n1, w1 = _kukri_profile(0.22)
    pc = S1 - n1 * (w1 * 0.5 - 0.002) + V((sx + 0.019, 0, 0))
    Sm.add_box(tuple(pc + V((0.0010, -0.0, 0.0))), (0.0100, 0.062, 0.028), mat=leather)
    parts['sheath'] = _finish(Sm, col, root, origin=(sx, -0.12, 0.0), bevel=0.0006)

    # ---------------------------------------------------------------- karda + chakmak (small knives)
    def small_knife(name, length, handle_len, ox, oy, oz, tilt):
        K = MeshBuilder(name)
        bl = length
        rr = []
        for i in range(8):
            t = i / 7
            wdt = 0.0085 * (1 - t ** 2.5) + 0.0004
            th = 0.0016 * (1 - t * 0.7)
            rr.append([V((th, -t * bl, 0.0)), V((0, -t * bl, wdt)), V((-th, -t * bl, 0.0)), V((0, -t * bl, -wdt * 0.2))])
        K.add_loft(rr, caps=True, mat=steel)
        hh = [(0.0075, 0.0070), (0.0095, 0.0085), (0.0100, 0.0090), (0.0090, 0.0080)]
        hr = []
        for j, (a, b) in enumerate(hh):
            y = 0.0 + j * handle_len / 3
            hr.append(ring_ellipse(V((0, y, 0)), V((1, 0, 0)), V((0, 0, 1)), a, b, 14))
        K.add_loft(hr, caps=True, mat=wood)
        K.add_cyl((0, -0.001, 0), (0, 0.003, 0), 0.0105, 0.0105, 14, mat=brass)
        ob = K.to_object(col, loc=(ox, oy, oz))
        ob.rotation_euler = Euler((0, 0, tilt))
        ob.parent = root
        return ob
    parts['karda'] = small_knife("Kukri_Karda", 0.095, 0.060, sx + 0.0205, -0.095, 0.014, 0.0)
    parts['chakmak'] = small_knife("Kukri_Chakmak", 0.085, 0.058, sx + 0.0205, -0.095, -0.010, 0.0)
    for k in ('karda', 'chakmak'):
        apply_bevel_safe(parts[k])

    # ---------------------------------------------------------------- attachment points
    _att("ATT_Grip_R", col, root, (0, 0.0, 0.0), size=0.03)
    _att("ATT_Sheath", col, root, (sx, 0.0, 0.0), size=0.03)
    _att("ATT_Belt_Frog", col, root, (sx - 0.026, -0.14, 0.006), size=0.02)
    _att("ATT_Tip", col, root, (0, -0.425, -0.082), size=0.02)
    return dict(root=root, parts=parts, name="Kukri")


def apply_bevel_safe(ob):
    try:
        add_bevel(ob, width=0.0003, segments=1, angle_deg=45)
    except Exception:
        pass


# =========================================================================================
# weapon-part animation (slide recoil, bolt, magazine swap, charging handle)
# =========================================================================================
FIRE_FRAMES = 8
RELOAD_FRAMES = 96
# (frame, dz, dy) offsets of the magazine relative to its seated pose; (frame, dy) for charging handle
MAG_KEYS = {
    'Handgun': [(1, 0.0, 0.0), (30, 0.0, 0.0), (40, -0.11, 0.03), (52, -0.30, 0.05), (56, -0.30, 0.05),
                (68, -0.12, 0.01), (80, -0.004, 0.0), (RELOAD_FRAMES, 0.0, 0.0)],
    'MachineGun': [(1, 0.0, 0.0), (28, 0.0, 0.0), (38, -0.10, -0.012), (50, -0.32, -0.02), (56, -0.32, -0.02),
                   (68, -0.14, -0.004), (80, -0.004, 0.0), (RELOAD_FRAMES, 0.0, 0.0)],
}
CH_KEYS = [(1, 0.0), (82, 0.0), (86, 0.045), (91, 0.0), (RELOAD_FRAMES, 0.0)]


def _key(ob, path, idx, frame, value, interp='BEZIER'):
    vec = list(getattr(ob, path))
    vec[idx] = value
    setattr(ob, path, vec)
    ob.keyframe_insert(path, index=idx, frame=frame)


def _finish_action(ob, name: str, frame_range: Tuple[int, int], cyclic=False):
    ad = ob.animation_data
    act = ad.action
    act.name = name
    act.use_fake_user = True
    act.use_frame_range = True
    act.frame_start, act.frame_end = frame_range
    act.use_cyclic = cyclic
    return act


def animate_weapon_parts(handgun, rifle) -> List[str]:
    """Create small object-level actions on weapon parts. Returns action names."""
    names = []
    # Handgun slide recoil
    sl = handgun['parts']['slide']
    sl.animation_data_create()
    base = sl.location.y
    for f, v in ((1, 0.0), (2, 0.022), (4, 0.0), (FIRE_FRAMES, 0.0)):
        _key(sl, 'location', 1, f, base + v)
    names.append(_finish_action(sl, "Handgun_Slide_Fire", (1, FIRE_FRAMES)).name)
    # Handgun trigger
    tr = handgun['parts']['trigger']
    tr.animation_data_create()
    for f, v in ((1, 0.0), (2, 0.006), (5, 0.0), (FIRE_FRAMES, 0.0)):
        _key(tr, 'location', 1, f, tr.location.y + v)
    names.append(_finish_action(tr, "Handgun_Trigger_Fire", (1, FIRE_FRAMES)).name)
    # Handgun magazine swap
    mg = handgun['parts']['magazine']
    mg.animation_data_create()
    z0, y0 = mg.location.z, mg.location.y
    for f, dz, dy in MAG_KEYS['Handgun']:
        _key(mg, 'location', 2, f, z0 + dz)
        _key(mg, 'location', 1, f, y0 + dy)
    names.append(_finish_action(mg, "Handgun_Magazine_Reload", (1, RELOAD_FRAMES)).name)
    # Rifle bolt recoil
    bo = rifle['parts']['bolt']
    bo.animation_data_create()
    by = bo.location.y
    for f, v in ((1, 0.0), (2, 0.034), (5, 0.0), (FIRE_FRAMES, 0.0)):
        _key(bo, 'location', 1, f, by + v)
    names.append(_finish_action(bo, "MG_Bolt_Fire", (1, FIRE_FRAMES)).name)
    # Rifle magazine swap
    rm = rifle['parts']['magazine']
    rm.animation_data_create()
    z0, y0 = rm.location.z, rm.location.y
    for f, dz, dy in MAG_KEYS['MachineGun']:
        _key(rm, 'location', 2, f, z0 + dz)
        _key(rm, 'location', 1, f, y0 + dy)
    names.append(_finish_action(rm, "MG_Magazine_Reload", (1, RELOAD_FRAMES)).name)
    # Charging handle rack at end of reload
    ch = rifle['parts']['charging_handle']
    ch.animation_data_create()
    cy = ch.location.y
    for f, v in CH_KEYS:
        _key(ch, 'location', 1, f, cy + v)
    names.append(_finish_action(ch, "MG_ChargingHandle_Reload", (1, RELOAD_FRAMES)).name)
    return names
