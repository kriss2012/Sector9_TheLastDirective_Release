"""Low-sample Cycles (CPU) preview renders for visual verification (works headless, no GPU)."""
from __future__ import annotations
import math
from typing import Iterable, Optional, Sequence, Tuple
import bpy
from mathutils import Vector

V = Vector


def _ensure_world():
    sc = bpy.context.scene
    if sc.world is None:
        sc.world = bpy.data.worlds.new("PreviewWorld")
    w = sc.world
    w.use_nodes = True
    bg = w.node_tree.nodes.get("Background")
    if bg:
        bg.inputs['Color'].default_value = (0.02, 0.022, 0.026, 1)
        bg.inputs['Strength'].default_value = 0.6


def _light(name, kind, loc, energy, rot=None, size=1.0, color=(1, 1, 1)):
    d = bpy.data.lights.new(name, kind)
    d.energy = energy
    d.color = color
    if kind == 'AREA':
        d.size = size
    ob = bpy.data.objects.new(name, d)
    bpy.context.scene.collection.objects.link(ob)
    ob.location = loc
    if rot:
        ob.rotation_euler = rot
    return ob


def render_view(path: str, target: Vector, eye: Vector, res=(900, 700), samples: int = 24,
                lens: float = 70.0, hide: Sequence[bpy.types.Object] = ()) -> str:
    sc = bpy.context.scene
    _ensure_world()
    sc.render.engine = 'CYCLES'
    try:
        sc.cycles.device = 'CPU'
        sc.cycles.samples = samples
        sc.cycles.use_denoising = False
    except Exception:
        pass
    sc.render.resolution_x, sc.render.resolution_y = res
    sc.render.resolution_percentage = 100
    sc.render.image_settings.file_format = 'PNG'
    sc.render.film_transparent = False
    try:
        sc.view_settings.view_transform = 'Filmic' if 'Filmic' in [i.identifier for i in sc.view_settings.bl_rna.properties['view_transform'].enum_items] else 'Standard'
    except Exception:
        pass
    cam_d = bpy.data.cameras.new("PrevCam")
    cam_d.lens = lens
    cam = bpy.data.objects.new("PrevCam", cam_d)
    sc.collection.objects.link(cam)
    cam.location = eye
    cam.rotation_euler = (target - eye).to_track_quat('-Z', 'Y').to_euler()
    sc.camera = cam
    lights = [
        _light("PL_key", 'AREA', target + V((-1.2, -1.6, 1.6)), 220, size=1.5, color=(1.0, 0.93, 0.85)),
        _light("PL_fill", 'AREA', target + V((1.8, -1.0, 0.6)), 80, size=2.0, color=(0.7, 0.8, 1.0)),
        _light("PL_rim", 'AREA', target + V((0.5, 1.8, 1.2)), 260, size=1.2, color=(1.0, 0.7, 0.45)),
    ]
    for l in lights:
        l.rotation_euler = (target - l.location).to_track_quat('-Z', 'Y').to_euler()
    sc.render.filepath = path
    bpy.ops.render.render(write_still=True)
    for l in lights:
        bpy.data.objects.remove(l, do_unlink=True)
    bpy.data.objects.remove(cam, do_unlink=True)
    return path
