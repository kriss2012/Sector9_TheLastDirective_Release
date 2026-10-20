"""Aged M1911-style pistol (matches pistol reference: dark worn slide, walnut
checkered grips, star-decorated trigger guard).  Origin = grip centre, +Y = muzzle.

blender --background --python tools/blender_assets/build_pistol.py -- --out assets/models
"""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *  # noqa: E402,F401,F403


def build():
    clear_scene()
    steel = make_material("PistolSteel", (0.07, 0.07, 0.08), 0.9, 0.38)
    bright = make_material("PistolBrightSteel", (0.55, 0.56, 0.58), 1.0, 0.25)
    wood = make_material("PistolWalnut", (0.30, 0.09, 0.05), 0.0, 0.45)
    star = make_material("PistolStar", (0.75, 0.75, 0.78), 1.0, 0.3)
    root = make_root("Pistol")

    # Frame (lower) + slide (upper)
    add_box("Frame", (0.030, 0.150, 0.026), (0, 0.020, 0.040), steel, 0.002, parent=root)
    add_box("Slide", (0.032, 0.200, 0.030), (0, 0.040, 0.074), steel, 0.002, parent=root)
    add_box("EjectionPort", (0.002, 0.040, 0.014), (0.0165, 0.030, 0.078), bright, parent=root)
    add_cyl("Barrel", 0.0095, 0.030, (0, 0.150, 0.074), "Y", bright, 20, parent=root)
    add_cyl("BarrelBushing", 0.0135, 0.016, (0, 0.136, 0.074), "Y", steel, 20, parent=root)

    # Serrations (rear and front)
    for i in range(10):
        add_box(f"SerRear{i}", (0.034, 0.0016, 0.026), (0, -0.040 + i * 0.0042, 0.074), steel, parent=root)
    for i in range(6):
        add_box(f"SerFront{i}", (0.034, 0.0016, 0.026), (0, 0.100 + i * 0.0042, 0.074), steel, parent=root)

    # Sights, hammer, safety
    add_box("FrontSight", (0.004, 0.008, 0.008), (0, 0.136, 0.093), steel, parent=root)
    add_box("RearSight", (0.014, 0.008, 0.008), (0, -0.052, 0.093), steel, parent=root)
    add_box("Hammer", (0.008, 0.016, 0.022), (0, -0.062, 0.070), steel, 0.001,
            rot=(math.radians(-25), 0, 0), parent=root)
    add_box("Safety", (0.004, 0.018, 0.008), (0.018, -0.040, 0.052), steel, parent=root)

    # Grip frame, backstrap, mainspring housing, magwell
    add_box("GripFrame", (0.028, 0.050, 0.095), (0, -0.024, -0.004), steel, 0.002,
            rot=(math.radians(-8), 0, 0), parent=root)
    add_box("MainspringHousing", (0.026, 0.012, 0.085), (0, -0.054, -0.004), steel, 0.002,
            rot=(math.radians(-8), 0, 0), parent=root)
    add_box("MagBase", (0.028, 0.050, 0.008), (0.0, -0.036, -0.056), steel, 0.002,
            rot=(math.radians(-8), 0, 0), parent=root)
    add_box("GripSafety", (0.010, 0.010, 0.040), (0, -0.054, 0.028), steel, parent=root)

    # Walnut grip panels with checkering strips (both sides)
    for side in (1, -1):
        add_box(f"GripPanel{side}", (0.006, 0.050, 0.092), (side * 0.0165, -0.024, -0.004),
                wood, 0.002, rot=(math.radians(-8), 0, 0), parent=root)
        for i in range(9):
            add_box(f"Checker{side}_{i}", (0.0008, 0.044, 0.0014),
                    (side * 0.0198, -0.024 + 0.0013 * (i % 2), -0.040 + i * 0.0095),
                    wood, rot=(math.radians(-8), 0, 0), parent=root)
        add_cyl(f"GripScrew{side}", 0.004, 0.003, (side * 0.0205, -0.026, 0.020 - 0.0), "X", steel, 12, parent=root)
        add_cyl(f"GripScrewB{side}", 0.004, 0.003, (side * 0.0205, -0.020, -0.044), "X", steel, 12, parent=root)

    # Trigger guard (torus section) + trigger + stars
    add_torus("TriggerGuard", 0.020, 0.0035, (0, 0.032, 0.014), "X", steel, parent=root)
    add_box("Trigger", (0.006, 0.008, 0.022), (0, 0.016, 0.026), bright, 0.001,
            rot=(math.radians(20), 0, 0), parent=root)
    for i in range(3):  # three stars on guard side, pentagon discs
        add_cyl(f"Star{i}", 0.0042, 0.0012, (0.0045, 0.040, 0.016 - 0.0 + i * 0.0 - 0.012 * (i - 1)),
                "X", star, 5, parent=root)

    # Sockets for the game / rig
    add_socket(root, "SOCKET_Muzzle", (0, 0.166, 0.074), (-math.pi / 2, 0, 0))
    add_socket(root, "SOCKET_Eject", (0.018, 0.030, 0.078))
    add_socket(root, "SOCKET_MagWell", (0, -0.036, -0.050))
    add_socket(root, "SOCKET_HandR", (0, -0.030, 0.000))
    return root


if __name__ == "__main__":
    out = parse_out_dir()
    export_asset(build(), out, "pistol_m1911")
