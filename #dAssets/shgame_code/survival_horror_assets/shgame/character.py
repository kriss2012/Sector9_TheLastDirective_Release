"""Assemble a full character (skin, head, hair, outfit, gear) as separate skinned-ready mesh objects."""
from __future__ import annotations
from typing import Dict, List

import bpy
import bmesh

from .config import CHARACTERS
from . import skeleton as SK
from . import body as BD
from . import outfit as OF
from .utils import (get_collection, apply_modifiers, shade_smooth_by_angle, mesh_stats, V, MeshBuilder)


def _solidify(ob: bpy.types.Object, thickness: float, offset: float = 1.0) -> None:
    m = ob.modifiers.new("Solidify", 'SOLIDIFY')
    m.thickness = thickness
    m.offset = offset
    m.use_even_offset = False
    try:
        m.nonmanifold_thickness_mode = 'CONSTRAINTS'
    except Exception:
        pass
    apply_modifiers(ob)


def build_character(kind: str, cfg, L: Dict[str, bpy.types.Material], parent_col) -> Dict:
    spec = CHARACTERS[kind]
    female = kind == "female"
    col = get_collection(f"CHR_{spec['name']}", parent_col)
    geo = get_collection(f"{spec['name']}_Meshes", col)
    T = SK.build_table(spec, female)
    seed = cfg.seed + (101 if female else 7)
    objs: Dict[str, bpy.types.Object] = {}

    mb = BD.build_body(spec, T, L, col, female, cfg)
    objs["body"] = mb.to_object(geo)
    objs["body"].name = f"{spec['name']}_Body"

    hmb, info = BD.build_head(spec, T, L, col, female, cfg)
    hbm = hmb.bm
    eyes = BD.build_eyes(spec, info, L, col, female)
    brows = BD.build_brows(spec, info, L, col, female)
    if female:
        scalp, pony = BD.build_hair_female(spec, hbm, info, L, T, seed)
        extra = {"hair": scalp, "ponytail": pony}
    else:
        hair = BD.build_hair_male(spec, hbm, info, L, seed)
        beard = BD.build_beard_from_bm(spec, hbm, info, L, seed)
        extra = {"hair": hair, "beard": beard}
    objs["head"] = hmb.to_object(geo)
    objs["head"].name = f"{spec['name']}_Head"
    objs["eyes"] = eyes.to_object(geo)
    objs["brows"] = brows.to_object(geo)
    for k_, m_ in extra.items():
        objs[k_] = m_.to_object(geo)

    parts = OF.build_outfit(spec, T, L, female, cfg, seed, info)
    for key in ("shirt", "pants", "boots", "gloves", "gear", "backpack"):
        objs[key] = parts[key].to_object(geo)
    objs["jacket"] = parts["jacket_core"].to_object(geo)
    objs["jacket"].name = f"{spec['name']}_Jacket"
    _solidify(objs["jacket"], 0.0065, 1.0)
    for key, o in objs.items():
        o.name = f"{spec['name']}_{key.capitalize()}" if not o.name.startswith(spec['name']) else o.name
        shade_smooth_by_angle(o, 55.0)
    return dict(kind=kind, spec=spec, female=female, table=T, objects=objs, collection=col, geo=geo, head_info=info)
