"""Third-person camera rig: pivot (follows the character) -> boom (driver-controlled offset) -> camera.

Custom properties on the pivot (all animatable):  distance, shoulder_offset, height, fov_deg, pitch_deg
Presets: DEFAULT, AIM, CROUCH, SPRINT  ->  ``set_mode(rig, 'AIM')``.
Drivers convert the properties into the boom's local location; a Track-To constraint keeps the camera aimed
at the pivot; a Copy-Location constraint makes the pivot follow the character's ``socket_camera_focus`` bone.
(Constraints / drivers are Blender-side conveniences; glTF stores the resulting camera node transform only.)
"""
from __future__ import annotations
import math
from typing import Dict

import bpy
from mathutils import Vector

MODES: Dict[str, Dict[str, float]] = {
    "DEFAULT": dict(distance=2.6, shoulder_offset=0.55, height=0.35, fov_deg=50.0, pitch_deg=8.0),
    "AIM": dict(distance=1.35, shoulder_offset=0.48, height=0.20, fov_deg=38.0, pitch_deg=3.0),
    "CROUCH": dict(distance=2.3, shoulder_offset=0.50, height=-0.25, fov_deg=50.0, pitch_deg=6.0),
    "SPRINT": dict(distance=3.1, shoulder_offset=0.25, height=0.45, fov_deg=62.0, pitch_deg=10.0),
}


def _driver(obj, path: str, index: int, owner, prop: str, expr: str = "v") -> None:
    fc = obj.driver_add(path, index)
    d = fc.driver
    d.type = 'SCRIPTED'
    var = d.variables.new()
    var.name = "v"
    var.type = 'SINGLE_PROP'
    var.targets[0].id = owner
    var.targets[0].data_path = f'["{prop}"]'
    d.expression = expr


def build_camera_rig(name: str, col, armature, scene, focus_bone: str = "socket_camera_focus", scale: float = 1.0):
    pivot = bpy.data.objects.new(f"{name}_CamPivot", None)
    pivot.empty_display_type = 'SPHERE'
    pivot.empty_display_size = 0.08
    col.objects.link(pivot)
    boom = bpy.data.objects.new(f"{name}_CamBoom", None)
    boom.empty_display_type = 'PLAIN_AXES'
    boom.empty_display_size = 0.1
    col.objects.link(boom)
    boom.parent = pivot
    cam_data = bpy.data.cameras.new(f"{name}_Camera")
    cam_data.sensor_fit = 'VERTICAL'
    cam_data.clip_start, cam_data.clip_end = 0.05, 200.0
    cam = bpy.data.objects.new(f"{name}_Camera", cam_data)
    col.objects.link(cam)
    cam.parent = boom
    # properties
    for k_, v_ in MODES["DEFAULT"].items():
        pivot[k_] = float(v_ * (scale if k_ in ("distance", "shoulder_offset", "height") else 1.0))
        pivot.id_properties_ui(k_).update(min=-5.0, max=20.0, soft_min=0.0, soft_max=10.0)
    pivot["mode"] = "DEFAULT"
    # drivers: boom location follows properties (character faces -Y, camera sits at +Y behind)
    _driver(boom, "location", 0, pivot, "shoulder_offset")
    _driver(boom, "location", 1, pivot, "distance")
    _driver(boom, "location", 2, pivot, "height")
    cam_data.sensor_height = 24.0
    fc = cam_data.driver_add("lens")
    d = fc.driver
    d.type = 'SCRIPTED'
    var = d.variables.new()
    var.name = "v"
    var.type = 'SINGLE_PROP'
    var.targets[0].id = pivot
    var.targets[0].data_path = '["fov_deg"]'
    d.expression = "12.0/tan(radians(v)/2.0)"
    # constraints
    cl = pivot.constraints.new('COPY_LOCATION')
    cl.target = armature
    cl.subtarget = focus_bone
    tt = cam.constraints.new('TRACK_TO')
    tt.target = pivot
    tt.track_axis = 'TRACK_NEGATIVE_Z'
    tt.up_axis = 'UP_Y'
    scene.camera = cam
    cam.location = (0, 0, 0)
    # at-rest transform (what glTF will contain): evaluate once
    boom.location = (pivot["shoulder_offset"], pivot["distance"], pivot["height"])
    return dict(pivot=pivot, boom=boom, camera=cam)


def set_mode(rig: Dict, mode: str, scale: float = 1.0) -> None:
    p = MODES[mode]
    for k_, v_ in p.items():
        rig["pivot"][k_] = float(v_ * (scale if k_ in ("distance", "shoulder_offset", "height") else 1.0))
    rig["pivot"]["mode"] = mode
    bpy.context.view_layer.update()
