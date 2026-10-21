"""Bake procedural node materials into image textures so that glTF/GLB contains real textures.

Per object & material slot three maps are produced (base colour, roughness, tangent-space normal);
a glTF-style ORM (G = roughness, B = metallic constant) is packed with numpy-free pure-Python-light code
via ``foreach_get`` when numpy is available (Blender ships it).  Original procedural materials are kept
untouched (``BK_`` clones carry the bake nodes; ``EX_`` materials are the export materials).
"""
from __future__ import annotations
import math
import os
from typing import Dict, List, Optional

import bpy

from .utils import set_active, unwrap_smart, BuildError


def res_for(obj: bpy.types.Object, base: int) -> int:
    d = max(obj.dimensions) if obj.dimensions.length > 0 else 1.0
    r = base
    if d < 0.12:
        r = base // 4
    elif d < 0.45:
        r = base // 2
    return max(128, min(base, r))


def _img(name: str, res: int, color: bool):
    img = bpy.data.images.new(name, res, res, alpha=False, float_buffer=False)
    img.colorspace_settings.name = 'sRGB' if color else 'Non-Color'
    return img


def _link_src(nt, node_name: str, sock_name: str):
    n = nt.nodes.get(node_name)
    if n is None:
        return None
    return n.outputs.get(sock_name) or n.outputs[0]


def bake_object(obj: bpy.types.Object, base_res: int, samples: int, out_dir: str) -> Dict[int, bpy.types.Material]:
    """Returns {slot_index: export_material}.  The object keeps BK_ materials during baking and is restored."""
    sc = bpy.context.scene
    sc.render.engine = 'CYCLES'
    sc.cycles.device = 'CPU'
    sc.cycles.samples = max(1, samples)
    sc.cycles.use_denoising = False
    if not obj.data.uv_layers:
        unwrap_smart(obj, margin=0.004)
    res = res_for(obj, base_res)
    originals = [s.material for s in obj.material_slots]
    clones, imgs = [], []
    for i, src in enumerate(originals):
        if src is None or not src.use_nodes:
            clones.append(None)
            imgs.append(None)
            continue
        mc = src.copy()
        mc.name = f"BK_{obj.name}_{i}"
        obj.material_slots[i].material = mc
        nt = mc.node_tree
        bc, ro, no = (_img(f"{obj.name}_{i}_BC", res, True), _img(f"{obj.name}_{i}_R", res, False),
                      _img(f"{obj.name}_{i}_N", res, False))
        nodes = {}
        for key, im in (("BC", bc), ("R", ro), ("N", no)):
            tn = nt.nodes.new('ShaderNodeTexImage')
            tn.image = im
            tn.name = f"BAKE_{key}"
            nodes[key] = tn
        clones.append(mc)
        imgs.append((bc, ro, no, nodes, src))
    set_active(obj)
    out_node_of = {}
    for i, mc in enumerate(clones):
        if mc is None:
            continue
        out_node_of[i] = next(n for n in mc.node_tree.nodes if n.type == 'OUTPUT_MATERIAL')

    def run(kind: str):
        for i, mc in enumerate(clones):
            if mc is None:
                continue
            nt = mc.node_tree
            bc, ro, no, nodes, src = imgs[i]
            for n in nt.nodes:
                n.select = False
            tn = nodes[{"EMIT_BC": "BC", "EMIT_R": "R", "NORMAL": "N"}[kind]]
            tn.select = True
            nt.nodes.active = tn
            out = out_node_of[i]
            for l in list(out.inputs['Surface'].links):
                nt.links.remove(l)
            if kind == "NORMAL":
                bsdf = next(n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED')
                nt.links.new(bsdf.outputs['BSDF'], out.inputs['Surface'])
            else:
                em = nt.nodes.new('ShaderNodeEmission')
                em.name = "BAKE_EMIT"
                key = "bc" if kind == "EMIT_BC" else "rough"
                s = _link_src(nt, src.get(f"{key}_socket_node"), src.get(f"{key}_socket_name"))
                if s is None:
                    raise BuildError(f"{src.name}: missing baked socket info")
                nt.links.new(s, em.inputs['Color'])
                nt.links.new(em.outputs['Emission'], out.inputs['Surface'])
        if kind == "NORMAL":
            bpy.ops.object.bake(type='NORMAL', margin=6, normal_space='TANGENT')
        else:
            bpy.ops.object.bake(type='EMIT', margin=6)
        for i, mc in enumerate(clones):
            if mc is None:
                continue
            em = mc.node_tree.nodes.get("BAKE_EMIT")
            if em:
                mc.node_tree.nodes.remove(em)

    run("EMIT_BC")
    run("EMIT_R")
    run("NORMAL")
    # export materials -----------------------------------------------------------------------------
    result: Dict[int, bpy.types.Material] = {}
    os.makedirs(out_dir, exist_ok=True)
    for i, mc in enumerate(clones):
        if mc is None:
            continue
        bc, ro, no, nodes, src = imgs[i]
        orm = _pack_orm(f"{obj.name}_{i}_ORM", ro, float(src.get("metallic_const", 0.0)))
        for im in (bc, no, orm):
            im.filepath_raw = os.path.join(out_dir, f"{im.name}.png")
            im.file_format = 'PNG'
            im.save()
        bpy.data.images.remove(ro)
        ex = bpy.data.materials.new(f"EX_{src.name}__{obj.name}_{i}")
        ex.use_nodes = True
        nt = ex.node_tree
        nt.nodes.clear()
        out = nt.nodes.new('ShaderNodeOutputMaterial')
        bs = nt.nodes.new('ShaderNodeBsdfPrincipled')
        nt.links.new(bs.outputs['BSDF'], out.inputs['Surface'])
        t_bc = nt.nodes.new('ShaderNodeTexImage')
        t_bc.image = bc
        nt.links.new(t_bc.outputs['Color'], bs.inputs['Base Color'])
        t_o = nt.nodes.new('ShaderNodeTexImage')
        t_o.image = orm
        sep = nt.nodes.new('ShaderNodeSeparateColor')
        nt.links.new(t_o.outputs['Color'], sep.inputs['Color'])
        nt.links.new(sep.outputs['Green'], bs.inputs['Roughness'])
        nt.links.new(sep.outputs['Blue'], bs.inputs['Metallic'])
        t_n = nt.nodes.new('ShaderNodeTexImage')
        t_n.image = no
        nm = nt.nodes.new('ShaderNodeNormalMap')
        nt.links.new(t_n.outputs['Color'], nm.inputs['Color'])
        nt.links.new(nm.outputs['Normal'], bs.inputs['Normal'])
        # carry over emission (sight reticle etc.)
        sb = next((n for n in src.node_tree.nodes if n.type == 'BSDF_PRINCIPLED'), None)
        if sb is not None:
            es = sb.inputs.get('Emission Strength')
            ec = sb.inputs.get('Emission Color')
            if es is not None and es.default_value > 0.0 and ec is not None:
                bs.inputs['Emission Color'].default_value = ec.default_value
                bs.inputs['Emission Strength'].default_value = es.default_value
        result[i] = ex
        for im in (bc, no, orm):          # free RAM: the exporter re-reads the saved PNGs
            im.buffers_free()
        # bake images are only needed by EX material now; keep clone out of export
    # restore the original procedural materials on the object
    for i, m in enumerate(originals):
        obj.material_slots[i].material = m
    for mc in clones:
        if mc is not None:
            bpy.data.materials.remove(mc)
    return result


def _pack_orm(name: str, rough_img: bpy.types.Image, metallic: float) -> bpy.types.Image:
    w, h = rough_img.size
    out = bpy.data.images.new(name, w, h, alpha=False)
    out.colorspace_settings.name = 'Non-Color'
    try:
        import numpy as np
        px = np.empty(w * h * 4, dtype=np.float32)
        rough_img.pixels.foreach_get(px)
        px = px.reshape(-1, 4)
        o = np.empty_like(px)
        o[:, 0] = 1.0
        o[:, 1] = px[:, 0]
        o[:, 2] = metallic
        o[:, 3] = 1.0
        out.pixels.foreach_set(o.reshape(-1))
    except ImportError:
        px = list(rough_img.pixels)
        o = [0.0] * len(px)
        for j in range(0, len(px), 4):
            o[j], o[j + 1], o[j + 2], o[j + 3] = 1.0, px[j], metallic, 1.0
        out.pixels = o
    return out


def bake_objects(objs: List[bpy.types.Object], base_res: int, samples: int, out_dir: str) -> Dict[str, Dict[int, bpy.types.Material]]:
    res = {}
    for ob in objs:
        if ob.type != 'MESH' or not ob.material_slots:
            continue
        # hide modifiers' influence (armature) – bake in rest pose
        res[ob.name] = bake_object(ob, base_res, samples, out_dir)
    return res


class swap_export_materials:
    """Context manager: temporarily replace slot materials by their baked EX_ versions."""

    def __init__(self, table: Dict[str, Dict[int, bpy.types.Material]]):
        self.table = table
        self.saved = {}

    def __enter__(self):
        for name, slots in self.table.items():
            ob = bpy.data.objects.get(name)
            if ob is None:
                continue
            self.saved[name] = [s.material for s in ob.material_slots]
            for i, m in slots.items():
                ob.material_slots[i].material = m
        return self

    def __exit__(self, *exc):
        for name, mats in self.saved.items():
            ob = bpy.data.objects.get(name)
            for i, m in enumerate(mats):
                ob.material_slots[i].material = m
