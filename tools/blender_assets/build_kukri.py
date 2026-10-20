"""Gurkha-style kukri with scabbard and two small utility knives (matches kukri
reference: forward-curved polished blade with fuller + cho notch, cross-hatched
dark wood handle, brass bolster and flared pommel, black leather scabbard with
brass tip, karda + chakmak).  Origin = handle centre, +Y = blade tip.

blender --background --python tools/blender_assets/build_kukri.py -- --out assets/models
"""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *  # noqa: E402,F401,F403


def blade_profile(length, steps=48, max_w=0.052, base_w=0.022, sag=0.085):
    """Return list of (y, z_spine, z_edge) along the blade, +Y forward.
    The blade drops (belly) then the tip rises back toward the spine line."""
    pts = []
    for i in range(steps + 1):
        t = i / steps
        y = length * t
        spine = -sag * t ** 2.2
        w = (base_w + (max_w - base_w) * math.sin(math.pi * min(1.0, t * 1.10) ** 0.9)) * (1 - t ** 7)
        pts.append((y, spine, spine - w))
    return pts


def build_blade(name, length, thickness, mat, parent, offset=(0, 0, 0), **kw):
    prof = blade_profile(length, **kw)
    ox, oy, oz = offset
    verts, faces = [], []
    # per station: spine-left, spine-right, edge
    for (y, zs, ze) in prof:
        verts += [(ox - thickness / 2, oy + y, oz + zs),
                  (ox + thickness / 2, oy + y, oz + zs),
                  (ox, oy + y, oz + ze)]
    n = len(prof)
    for i in range(n - 1):
        a, b = i * 3, (i + 1) * 3
        faces += [[a, b, b + 1, a + 1],        # spine top
                  [a, a + 2, b + 2, b],        # left bevel
                  [a + 1, b + 1, b + 2, a + 2]]  # right bevel
    # base cap
    faces.append([0, 1, 2])
    return mesh_from_pydata(name, verts, faces, mat, parent)


def build():
    clear_scene()
    steel = make_material("KukriSteel", (0.72, 0.73, 0.75), 1.0, 0.22)
    wood = make_material("KukriDarkWood", (0.07, 0.045, 0.03), 0.0, 0.35)
    brass = make_material("KukriBrass", (0.80, 0.60, 0.20), 1.0, 0.30)
    leather = make_material("KukriLeather", (0.02, 0.02, 0.022), 0.0, 0.70)
    root = make_root("Kukri")

    # ---------------- Kukri: blade
    build_blade("Blade", 0.340, 0.006, steel, root, offset=(0, 0.060, 0))
    # fuller (groove) suggested by a raised thin strip on each side
    for s in (1, -1):
        add_box(f"Fuller{s}", (0.0012, 0.200, 0.006), (s * 0.0032, 0.200, -0.018),
                steel, rot=(math.radians(-6), 0, 0), parent=root)
    # cho notch (cut-out look: dark disc at the blade/handle junction)
    add_cyl("ChoNotch", 0.006, 0.0075, (0, 0.092, -0.022), "X", wood, 16, parent=root)

    # ---------------- Handle
    add_cyl("Bolster", 0.0165, 0.016, (0, 0.056, 0), "Y", brass, 24, bevel=0.001, parent=root)
    add_cyl("Grip", 0.0155, 0.100, (0, 0.000, 0), "Y", wood, 24, radius2=0.0185, parent=root)
    for i in range(14):  # cross-hatch ribs
        add_torus(f"GripRib{i}", 0.0170 + (i * 0.00012), 0.0012, (0, 0.046 - i * 0.0075, 0), "Y", wood, parent=root)
    add_cyl("PommelNeck", 0.0165, 0.020, (0, -0.058, 0), "Y", wood, 24, parent=root)
    add_cyl("Pommel", 0.024, 0.016, (0, -0.075, 0), "Y", wood, 24, radius2=0.0175, parent=root)
    add_cyl("PommelRim", 0.0255, 0.003, (0, -0.0845, 0), "Y", brass, 24, parent=root)
    add_cyl("PommelRivet", 0.004, 0.004, (0, -0.0855, 0), "Y", brass, 12, parent=root)

    # ---------------- Scabbard (separate object group, lying beside the kukri)
    scab = make_root("Scabbard", loc=(0.12, 0, 0))
    scab.parent = root
    verts, faces = [], []
    L, hw, th = 0.380, 0.060, 0.018
    stations = 24
    for i in range(stations + 1):
        t = i / stations
        y = -0.020 + L * t
        z = -0.090 * t ** 2.2
        w = hw * (0.55 + 0.45 * math.sin(math.pi * min(1.0, t * 1.05))) * (1 - 0.65 * t ** 4)
        verts += [(-th, y, z + w), (th, y, z + w), (th, y, z - w), (-th, y, z - w)]
    for i in range(stations):
        a, b = i * 4, (i + 1) * 4
        for k in range(4):
            k2 = (k + 1) % 4
            faces.append([a + k, a + k2, b + k2, b + k])
    faces.append([3, 2, 1, 0])
    mesh_from_pydata("ScabbardBody", verts, faces, leather, scab)
    add_cyl("ScabbardTip", 0.020, 0.040, (0, 0.375, -0.090), "Y", brass, 12, radius2=0.004, parent=scab)
    add_box("ScabbardMouth", (0.040, 0.012, 0.100), (0, -0.018, 0.0), brass, 0.002, parent=scab)
    add_box("FrogStrap", (0.044, 0.040, 0.015), (0, 0.050, 0.060), leather, 0.002, parent=scab)

    # ---------------- Karda + chakmak (small knives on scabbard face)
    for name, off in (("Karda", (0.0, 0.0)), ("Chakmak", (0.0, -0.030))):
        small = make_root(name, loc=(0.12 + 0.022, 0.150, 0.015 + off[1]))
        small.parent = root
        small.rotation_euler = (0, 0, math.radians(8))
        build_blade(name + "Blade", 0.075, 0.003, steel, small, offset=(0, 0.015, 0),
                    max_w=0.012, base_w=0.008, sag=0.004, steps=16)
        add_cyl(name + "Handle", 0.007, 0.050, (0, -0.013, 0), "Y", wood, 12, radius2=0.0085, parent=small)
        add_cyl(name + "Guard", 0.0085, 0.004, (0, 0.012, 0), "Y", brass, 12, parent=small)

    # ---------------- Sockets
    add_socket(root, "SOCKET_HandR", (0, 0.000, 0))
    add_socket(root, "SOCKET_BladeTip", (0, 0.400, -0.085))
    add_socket(root, "SOCKET_Sheath", (0.12, 0.100, 0.0))
    return root


if __name__ == "__main__":
    out = parse_out_dir()
    export_asset(build(), out, "knife_kukri")
