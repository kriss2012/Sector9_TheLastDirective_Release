"""Export helpers (.blend and .glb)."""
from __future__ import annotations
import os
from typing import Iterable, Optional, Sequence

import bpy

from .utils import BuildError, set_active


def _enable_gltf():
    try:
        bpy.ops.preferences.addon_enable(module='io_scene_gltf2')
    except Exception:
        pass
    if not hasattr(bpy.ops.export_scene, 'gltf'):
        raise BuildError("glTF exporter add-on (io_scene_gltf2) is not available")


def save_blend(path: str, compress: bool = True) -> str:
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=path, compress=compress)
    return path


def _filter(**kw):
    props = set(bpy.ops.export_scene.gltf.get_rna_type().properties.keys())
    return {k: v for k, v in kw.items() if k in props}


def export_glb(path: str, objects: Optional[Sequence[bpy.types.Object]] = None, animations: bool = True,
               cameras: bool = False) -> str:
    """Export selected objects (or the whole scene) to a single self-contained .glb."""
    _enable_gltf()
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    for o in bpy.context.view_layer.objects:
        o.select_set(False)
    if objects:
        for o in objects:
            o.select_set(True)
        bpy.context.view_layer.objects.active = objects[0]
    kw = _filter(filepath=path, export_format='GLB', use_selection=bool(objects), export_animations=animations,
                 export_animation_mode='NLA_TRACKS', export_skins=True, export_morph=True, export_apply=False,
                 export_yup=True, export_cameras=cameras, export_extras=True, export_image_format='AUTO',
                 export_optimize_animation_size=False, export_force_sampling=True, export_lights=False,
                 export_def_bones=False, export_anim_single_armature=False)
    res = bpy.ops.export_scene.gltf(**kw)
    if 'FINISHED' not in res or not os.path.exists(path):
        raise BuildError(f"glTF export failed for {path}: {res}")
    return path
