"""Tactical carbine (matches rifle reference: brass-toned receiver, black slotted
handguard, collapsible stock, red-dot sight, vertical foregrip, slab magazine,
birdcage flash hider).  Origin = pistol-grip centre, +Y = muzzle.

blender --background --python tools/blender_assets/build_rifle.py -- --out assets/models
"""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *  # noqa: E402,F401,F403


def build():
    clear_scene()
    black = make_material("RifleBlackPolymer", (0.025, 0.025, 0.028), 0.1, 0.55)
    brass = make_material("RifleBrassReceiver", (0.55, 0.40, 0.17), 0.85, 0.40)
    steel = make_material("RifleSteel", (0.45, 0.45, 0.47), 1.0, 0.30)
    dark = make_material("RifleDarkSteel", (0.06, 0.06, 0.07), 0.9, 0.40)
    glass = make_material("RifleOpticGlass", (0.05, 0.12, 0.15), 0.0, 0.05)
    root = make_root("Rifle")

    # --- Receiver (brass) upper + lower, ejection port, rail
    add_box("UpperReceiver", (0.040, 0.240, 0.050), (0, 0.150, 0.075), brass, 0.002, parent=root)
    add_box("LowerReceiver", (0.038, 0.170, 0.058), (0, 0.075, 0.020), brass, 0.002, parent=root)
    add_box("TopRail", (0.022, 0.300, 0.010), (0, 0.170, 0.105), dark, parent=root)
    for i in range(14):
        add_box(f"RailSlot{i}", (0.024, 0.004, 0.011), (0, 0.040 + i * 0.020, 0.105), black, parent=root)
    add_box("EjectionPort", (0.002, 0.050, 0.020), (0.0205, 0.150, 0.080), dark, parent=root)
    add_cyl("ChargingKnob", 0.007, 0.012, (0.026, 0.060, 0.090), "X", black, 12, parent=root)
    add_box("SelectorSwitch", (0.004, 0.020, 0.008), (0.021, 0.030, 0.040), black, parent=root)

    # --- Pistol grip, trigger guard, trigger
    add_box("PistolGrip", (0.034, 0.045, 0.100), (0, -0.002, -0.040), black, 0.004,
            rot=(math.radians(-18), 0, 0), parent=root)
    for i in range(5):
        add_box(f"GripRib{i}", (0.036, 0.040, 0.003), (0, -0.004 - i * 0.004, -0.020 - i * 0.016),
                dark, rot=(math.radians(-18), 0, 0), parent=root)
    add_torus("TriggerGuard", 0.022, 0.003, (0, 0.040, 0.000), "X", dark, parent=root)
    add_box("Trigger", (0.006, 0.008, 0.022), (0, 0.032, 0.006), steel, 0.001,
            rot=(math.radians(18), 0, 0), parent=root)

    # --- Magazine (ribbed slab, slight rearward curve)
    add_box("Magazine", (0.032, 0.058, 0.150), (0, 0.082, -0.080), black, 0.003,
            rot=(math.radians(-8), 0, 0), parent=root)
    for i in range(7):
        add_box(f"MagRib{i}", (0.034, 0.060, 0.0025), (0, 0.082 - i * 0.0012, -0.030 - i * 0.017),
                dark, rot=(math.radians(-8), 0, 0), parent=root)

    # --- Stock: buffer tube + butt + cheek brace
    add_cyl("BufferTube", 0.017, 0.200, (0, -0.130, 0.078), "Y", black, 20, parent=root)
    for i in range(9):
        add_torus(f"TubeRing{i}", 0.0175, 0.0015, (0, -0.040 - i * 0.020, 0.078), "Y", dark, parent=root)
    add_box("ButtPad", (0.040, 0.030, 0.105), (0, -0.245, 0.060), black, 0.006, parent=root)
    add_box("StockBody", (0.036, 0.160, 0.060), (0, -0.160, 0.068), black, 0.005, parent=root)
    add_box("StockLatch", (0.018, 0.030, 0.006), (0, -0.090, 0.040), dark, parent=root)

    # --- Handguard (black, slotted), barrel nut, gas block, barrel, flash hider
    add_box("Handguard", (0.052, 0.280, 0.058), (0, 0.430, 0.078), black, 0.006, parent=root)
    for i in range(8):  # oval vent slots
        add_box(f"HGSlot{i}", (0.054, 0.016, 0.010), (0, 0.320 + i * 0.026, 0.092), dark,
                bevel=0.003, parent=root)
    for i in range(4):
        add_box(f"HGLine{i}", (0.054, 0.200, 0.002), (0, 0.440, 0.052 + i * 0.008), dark, parent=root)
    add_box("HGRailBottom", (0.020, 0.200, 0.008), (0, 0.440, 0.044), dark, parent=root)
    add_cyl("Barrel", 0.0085, 0.360, (0, 0.560, 0.078), "Y", steel, 20, parent=root)
    add_cyl("GasBlock", 0.014, 0.050, (0, 0.585, 0.078), "Y", brass, 16, parent=root)
    add_cyl("GasTube", 0.006, 0.280, (0, 0.480, 0.098), "Y", steel, 12, parent=root)
    add_cyl("FlashHider", 0.0135, 0.062, (0, 0.725, 0.078), "Y", dark, 20, parent=root)
    for i in range(6):  # birdcage slots
        a = i * math.pi / 3
        add_box(f"FHSlot{i}", (0.004, 0.034, 0.004),
                (0.0135 * math.cos(a), 0.730, 0.078 + 0.0135 * math.sin(a)), black,
                rot=(0, a, 0), parent=root)
    # Front sight post + base
    add_box("FrontSightBase", (0.022, 0.024, 0.040), (0, 0.690, 0.100), steel, 0.002, parent=root)
    add_box("FrontSightPost", (0.003, 0.003, 0.028), (0, 0.690, 0.134), steel, parent=root)
    add_box("RearSight", (0.020, 0.014, 0.022), (0, 0.040, 0.124), dark, 0.002, parent=root)

    # --- Vertical foregrip
    add_cyl("ForegripStem", 0.012, 0.020, (0, 0.520, 0.032), "Z", dark, 12, parent=root)
    add_cyl("Foregrip", 0.017, 0.100, (0, 0.520, -0.030), "Z", black, 16, radius2=0.014, parent=root)
    for i in range(5):
        add_torus(f"ForegripRing{i}", 0.0165, 0.002, (0, 0.520, -0.005 - i * 0.017), "Z", dark, parent=root)

    # --- Holographic/red-dot sight
    add_box("OpticMount", (0.030, 0.060, 0.014), (0, 0.175, 0.118), dark, 0.002, parent=root)
    add_box("OpticBody", (0.040, 0.085, 0.050), (0, 0.175, 0.150), black, 0.006, parent=root)
    add_box("OpticGlass", (0.034, 0.002, 0.040), (0, 0.2165, 0.152), glass, parent=root)
    add_cyl("OpticDial", 0.010, 0.006, (0.0245, 0.165, 0.148), "X", steel, 12, parent=root)

    # --- Sockets: left-hand support, right hand, muzzle, eject, mag
    add_socket(root, "SOCKET_HandR", (0, 0.000, -0.020))
    add_socket(root, "SOCKET_HandL", (0, 0.520, -0.020))
    add_socket(root, "SOCKET_Muzzle", (0, 0.760, 0.078), (-math.pi / 2, 0, 0))
    add_socket(root, "SOCKET_Eject", (0.022, 0.150, 0.080))
    add_socket(root, "SOCKET_MagWell", (0, 0.082, -0.020))
    add_socket(root, "SOCKET_Sight", (0, 0.175, 0.152))
    return root


if __name__ == "__main__":
    out = parse_out_dir()
    export_asset(build(), out, "rifle_carbine")
