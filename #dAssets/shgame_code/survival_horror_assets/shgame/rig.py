"""Armature creation, skin binding, facial shape keys, weapon sockets / attachment."""
from __future__ import annotations
import math
from typing import Dict, List, Optional

import bpy
from mathutils import Vector, Matrix, Euler

from .utils import V, set_active, link_only, new_empty, gauss, smoothstep, BuildError
from . import skeleton as SK


def create_armature(name: str, T, col) -> bpy.types.Object:
    arm_data = bpy.data.armatures.new(name)
    arm = bpy.data.objects.new(name, arm_data)
    col.objects.link(arm)
    set_active(arm)
    bpy.ops.object.mode_set(mode='EDIT')
    ebs = {}
    for bn, d in T.items():
        eb = arm_data.edit_bones.new(bn)
        eb.head, eb.tail = d["head"], d["tail"]
        if (eb.tail - eb.head).length < 1e-4:
            eb.tail = eb.head + V((0, 0, 0.01))
        ebs[bn] = eb
    for bn, d in T.items():
        if d["parent"]:
            ebs[bn].parent = ebs[d["parent"]]
        ebs[bn].use_connect = False
        ebs[bn].use_deform = bool(d["deform"])
        vec = ebs[bn].tail - ebs[bn].head
        ref = V((0, -1, 0)) if abs(vec.z) > abs(vec.y) else V((0, 0, 1))
        try:
            ebs[bn].align_roll(ref)
        except Exception:
            pass
    bpy.ops.object.mode_set(mode='OBJECT')
    arm_data.display_type = 'OCTAHEDRAL'
    arm.show_in_front = True
    # bone collections (Blender 4.0+)
    try:
        cols = {n: arm_data.collections.new(n) for n in ("Deform", "Fingers", "Sockets", "Hair", "Root")}
        for bn, d in T.items():
            tag = d["tag"]
            c = cols["Sockets"] if tag == "socket" else cols["Fingers"] if tag == "finger" else cols["Hair"] if tag == "hair" \
                else cols["Root"] if bn == "root" else cols["Deform"]
            c.assign(arm_data.bones[bn])
    except Exception:
        pass
    return arm


def limit_and_normalize(obj: bpy.types.Object, max_infl: int = 4) -> None:
    """Clamp influences per vertex and normalise (game-engine friendly)."""
    me = obj.data
    vg = obj.vertex_groups
    for v in me.vertices:
        g = [(e.group, e.weight) for e in v.groups if e.weight > 1e-4]
        if len(g) > max_infl:
            g.sort(key=lambda t: -t[1])
            for gi, _ in g[max_infl:]:
                vg[gi].remove([v.index])
            g = g[:max_infl]
        tot = sum(w for _, w in g)
        if tot > 0 and abs(tot - 1.0) > 1e-4:
            for gi, w in g:
                vg[gi].add([v.index], w / tot, 'REPLACE')


def bind_mesh(obj: bpy.types.Object, arm: bpy.types.Object, max_infl: int = 4) -> None:
    obj.parent = arm
    obj.matrix_parent_inverse = Matrix.Identity(4)
    mod = obj.modifiers.new("Armature", 'ARMATURE')
    mod.object = arm
    mod.use_vertex_groups = True
    limit_and_normalize(obj, max_infl)


def add_face_shape_keys(head: bpy.types.Object, info: Dict, female: bool) -> List[str]:
    """Simple FACS-inspired corrective shapes: jaw_open, smile, brow_down, brow_up, blink_squint."""
    c, h, LM = info["center"], info["h"], info["LM"]
    mz = c.z + LM['mouth_z']
    me = head.data
    head.shape_key_add(name="Basis", from_mix=False)

    def key(name, fn):
        sk = head.shape_key_add(name=name, from_mix=False)
        for i, v in enumerate(me.vertices):
            rel = v.co - c
            sk.data[i].co = v.co + fn(rel)
        return name

    def jaw(rel):
        w = smoothstep(LM['mouth_z'] + 0.004 * h, LM['mouth_z'] - 0.03 * h, rel.z) * smoothstep(0.02, -0.04, rel.y * 1.0 + 0.0) * 1.0
        w *= smoothstep(-0.10, 0.02, -rel.y + 0.06) if rel.y < 0 else 0.4
        w = max(0.0, min(1.0, w))
        return V((0, 0.006, -0.020 * h)) * w * (1.0 if rel.y < 0.03 else 0.0)

    def smile(rel):
        ax = abs(rel.x)
        w = gauss(ax - 0.030, 0.012) * gauss(rel.z - LM['mouth_z'], 0.010 * h) * (1.0 if rel.y < -0.04 else 0.0)
        return V((math.copysign(0.005, rel.x), -0.001, 0.0065 * h)) * w

    def brow_down(rel):
        w = gauss(rel.z - LM['brow_z'], 0.013 * h) * smoothstep(0.07, 0.0, abs(rel.x)) * (1.0 if rel.y < -0.04 else 0.0)
        return V((0, -0.002, -0.006 * h)) * w

    def brow_up(rel):
        w = gauss(rel.z - LM['brow_z'], 0.013 * h) * smoothstep(0.07, 0.0, abs(rel.x)) * (1.0 if rel.y < -0.04 else 0.0)
        return V((0, 0.0, 0.007 * h)) * w

    def squint(rel):
        w = gauss(abs(rel.x) - info["eye_x"], 0.014) * gauss(rel.z - (LM['eye_z'] + 0.010 * h), 0.006 * h) * (1.0 if rel.y < -0.05 else 0.0)
        return V((0, -0.0015, -0.007 * h)) * w

    return [key("jaw_open", jaw), key("smile", smile), key("brow_down", brow_down), key("brow_up", brow_up),
            key("blink_squint", squint)]


def bone_world_rest(arm: bpy.types.Object, bone: str) -> Matrix:
    return arm.matrix_world @ arm.data.bones[bone].matrix_local


def attach_to_bone(obj: bpy.types.Object, arm: bpy.types.Object, bone: str, desired_world: Matrix) -> None:
    """Parent obj to a bone so that at rest it sits at desired_world (armature space = world)."""
    bpy.context.view_layer.update()
    b = arm.data.bones[bone]
    parent_mat = arm.matrix_world @ b.matrix_local @ Matrix.Translation((0, b.length, 0))
    obj.parent = arm
    obj.parent_type = 'BONE'
    obj.parent_bone = bone
    obj.matrix_parent_inverse = parent_mat.inverted() @ desired_world
    obj.location = (0, 0, 0)
    obj.rotation_euler = (0, 0, 0)
    obj.scale = (1, 1, 1)


def grip_rest_matrix(arm, T, side: str, grip_local: Vector, pitch_deg: float, shift: Vector = V((0, 0, 0))) -> Matrix:
    """Weapon-root world matrix at rest-pose for a weapon held by ``hand_<side>`` (see animations.py for derivation)."""
    sg = 1.0 if side == "L" else -1.0
    sock = T[f"socket_weapon_{side}"]["head"]
    R = Euler((math.radians(90.0 + pitch_deg), 0, 0)).to_matrix().to_4x4()
    M = Matrix.Translation(sock + V((-sg * 0.0, 0, 0)) + shift) @ R
    return M @ Matrix.Translation(-grip_local)


def add_weapon_sockets_info(arm: bpy.types.Object) -> Dict[str, str]:
    return {b.name: (b.parent.name if b.parent else "") for b in arm.data.bones if b.name.startswith("socket_")}
