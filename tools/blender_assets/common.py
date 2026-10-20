"""Shared helpers for the Sector9 Blender asset generators.

Run any build_*.py from Blender, e.g.:
    blender --background --python tools/blender_assets/build_pistol.py -- --out assets/models

Conventions (all scripts): metres, +Y = forward / muzzle direction, +Z = up,
+X = character's left side as seen from behind. Weapon origin = grip centre.
"""
import math
import os
import sys

import bpy
import bmesh
from mathutils import Vector


# ----------------------------------------------------------------- CLI / scene
def parse_out_dir(default="assets/models"):
    argv = sys.argv
    args = argv[argv.index("--") + 1:] if "--" in argv else []
    out = default
    if "--out" in args:
        out = args[args.index("--out") + 1]
    out = os.path.abspath(out)
    os.makedirs(out, exist_ok=True)
    return out


def clear_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)


# ------------------------------------------------------------------- materials
def make_material(name, color, metallic=0.0, roughness=0.5):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = (*color[:3], 1.0)
    bsdf.inputs["Metallic"].default_value = metallic
    bsdf.inputs["Roughness"].default_value = roughness
    mat.diffuse_color = (*color[:3], 1.0)
    return mat


# ------------------------------------------------------------------ primitives
def _finish(obj, name, mat, bevel, parent):
    obj.name = name
    obj.data.name = name
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
    if bevel > 0:
        mod = obj.modifiers.new("Bevel", "BEVEL")
        mod.width = bevel
        mod.segments = 2
        mod.limit_method = "ANGLE"
    if mat is not None:
        obj.data.materials.append(mat)
    if parent is not None:
        obj.parent = parent
    obj.select_set(False)
    return obj


def add_box(name, size, loc, mat=None, bevel=0.0, rot=(0, 0, 0), parent=None):
    """size = full (x, y, z) extents in metres."""
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc, rotation=rot)
    obj = bpy.context.active_object
    obj.scale = size
    return _finish(obj, name, mat, bevel, parent)


def add_cyl(name, radius, length, loc, axis="Y", mat=None, verts=24,
            bevel=0.0, radius2=None, parent=None):
    """Cylinder/cone along `axis`. radius2 gives a taper (top radius)."""
    rot = {"X": (0, math.pi / 2, 0), "Y": (-math.pi / 2, 0, 0), "Z": (0, 0, 0)}[axis]
    if radius2 is None:
        bpy.ops.mesh.primitive_cylinder_add(
            vertices=verts, radius=radius, depth=length, location=loc, rotation=rot)
    else:
        bpy.ops.mesh.primitive_cone_add(
            vertices=verts, radius1=radius, radius2=radius2, depth=length,
            location=loc, rotation=rot)
    return _finish(bpy.context.active_object, name, mat, bevel, parent)


def add_sphere(name, radius, loc, mat=None, scale=(1, 1, 1), parent=None):
    bpy.ops.mesh.primitive_uv_sphere_add(radius=radius, location=loc, segments=24, ring_count=16)
    obj = bpy.context.active_object
    obj.scale = scale
    return _finish(obj, name, mat, 0.0, parent)


def add_torus(name, major, minor, loc, axis="X", mat=None, parent=None):
    rot = {"X": (0, math.pi / 2, 0), "Y": (math.pi / 2, 0, 0), "Z": (0, 0, 0)}[axis]
    bpy.ops.mesh.primitive_torus_add(
        major_radius=major, minor_radius=minor, location=loc, rotation=rot,
        major_segments=32, minor_segments=12)
    return _finish(bpy.context.active_object, name, mat, 0.0, parent)


def mesh_from_pydata(name, verts, faces, mat=None, parent=None):
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata([tuple(v) for v in verts], [], faces)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    bm = bmesh.new()
    bm.from_mesh(mesh)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(mesh)
    bm.free()
    if mat is not None:
        obj.data.materials.append(mat)
    if parent is not None:
        obj.parent = parent
    return obj


# ------------------------------------------------------------------- finishing
def make_root(name, loc=(0, 0, 0)):
    root = bpy.data.objects.new(name, None)
    root.empty_display_type = "PLAIN_AXES"
    root.location = loc
    bpy.context.collection.objects.link(root)
    return root


def smooth_all(root):
    for obj in root.children_recursive:
        if obj.type == "MESH":
            for poly in obj.data.polygons:
                poly.use_smooth = True
            if "Bevel" not in obj.modifiers:
                continue


def add_socket(root, name, loc, rot=(0, 0, 0)):
    """Empty used by the game to attach hands, muzzle flash, ejection port, etc."""
    sock = bpy.data.objects.new(name, None)
    sock.empty_display_type = "ARROWS"
    sock.empty_display_size = 0.03
    sock.location = loc
    sock.rotation_euler = rot
    sock.parent = root
    bpy.context.collection.objects.link(sock)
    return sock


def export_asset(root, out_dir, basename):
    """Save <basename>.blend and <basename>.glb into out_dir."""
    smooth_all(root)
    blend_path = os.path.join(out_dir, basename + ".blend")
    glb_path = os.path.join(out_dir, basename + ".glb")
    bpy.ops.wm.save_as_mainfile(filepath=blend_path)
    bpy.ops.export_scene.gltf(filepath=glb_path, export_format="GLB",
                              export_apply=True, use_selection=False)
    print("[Sector9] wrote", blend_path)
    print("[Sector9] wrote", glb_path)
