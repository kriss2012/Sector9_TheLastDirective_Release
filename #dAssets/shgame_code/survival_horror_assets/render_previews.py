#!/usr/bin/env python3
"""Render low-sample Cycles previews from the generated .blend (CPU, works headless).

    blender -b output/survival_horror_assets.blend --python render_previews.py -- --out output/previews
    (or) python render_previews.py --blend output/survival_horror_assets.blend --out output/previews
"""
import argparse, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import bpy
from mathutils import Vector as V
from shgame import preview

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
ap = argparse.ArgumentParser()
ap.add_argument("--blend", default=None)
ap.add_argument("--out", default="previews")
ap.add_argument("--samples", type=int, default=24)
a = ap.parse_args(argv)
if a.blend:
    bpy.ops.wm.open_mainfile(filepath=os.path.abspath(a.blend))
os.makedirs(a.out, exist_ok=True)

SHOTS = [("Male", "Idle", 0, "front"), ("Male", "Aim_Rifle", 0, "side"), ("Male", "Run", 6, "side"),
         ("Female", "Idle", 0, "front"), ("Female", "Aim_Pistol", 0, "side"), ("Female", "Crouch", 60, "side"),
         ("Female", "Sit", 80, "side"), ("Male", "Reload_Rifle", 45, "side")]
for who, act, frame, view in SHOTS:
    arm = bpy.data.objects.get(f"{who}_Armature")
    action = bpy.data.actions.get(f"{who}_{act}")
    if arm is None or action is None:
        continue
    # isolate this character (hide the other one + its equipment from the render)
    for o in bpy.data.objects:
        mine = o.name.startswith(who) or o == arm or (o.parent is not None and o.parent == arm)
        other_char = any(o.name.startswith(x) for x in ("Male", "Female")) and not o.name.startswith(who)
        o.hide_render = bool(other_char) or (o.name.startswith("WPN_") or o.name.split("_")[0] in ("Handgun", "MG", "Kukri"))
    ad = arm.animation_data
    for t in ad.nla_tracks:
        t.mute = True
    ad.action = action
    bpy.context.scene.frame_set(frame)
    bpy.context.view_layer.update()
    c = arm.matrix_world.translation + V((0, 0, 0.95))
    eye = c + (V((3.4, 0, 0.15)) if view == "side" else V((0, -3.4, 0.15)))
    preview.render_view(os.path.join(a.out, f"{who}_{act}_{frame}_{view}.png"), c, eye, res=(520, 780), samples=a.samples, lens=60)
