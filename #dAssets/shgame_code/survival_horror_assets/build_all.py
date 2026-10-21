#!/usr/bin/env python3
"""Survival-horror asset pipeline (Blender / bpy).

Run inside Blender (GUI or background) ...
    blender --background --python build_all.py -- --out ./output
... or with the PyPI ``bpy`` wheel (Python 3.11/3.13 matching your bpy build):
    python build_all.py --out ./output

Options (after ``--`` when run through Blender):
    --out DIR            output directory (default ./output)
    --seed N             deterministic seed (default 1337)
    --no-bake            skip texture baking (GLB then has flat PBR factors only -> still valid)
    --res N              bake resolution per material (default 1024)
    --fast               head_segments 64, bake res 512 (quick iteration)
    --only male|female|weapons   build a subset
    --previews           also render Cycles preview PNGs
"""
from __future__ import annotations
import argparse
import json
import math
import os
import re
import sys
import time
import traceback

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import bpy
from mathutils import Matrix, Vector

from shgame import utils, materials, weapons, character, rig, animations, camera_rig, bake, export, validate
from shgame.config import BuildConfig, CHARACTERS

V = Vector


def parse_args(argv=None) -> BuildConfig:
    if argv is None:
        argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", default="output")
    ap.add_argument("--seed", type=int, default=1337)
    ap.add_argument("--no-bake", action="store_true")
    ap.add_argument("--res", type=int, default=1024)
    ap.add_argument("--fast", action="store_true")
    ap.add_argument("--only", choices=["male", "female", "weapons"])
    ap.add_argument("--previews", action="store_true")
    a = ap.parse_args(argv)
    cfg = BuildConfig(seed=a.seed, output_dir=os.path.abspath(a.out), bake_textures=not a.no_bake,
                      bake_resolution=a.res, render_previews=a.previews)
    if a.fast:
        cfg.head_segments, cfg.bake_resolution = 64, 512
    if a.only:
        cfg.build_male = a.only == "male"
        cfg.build_female = a.only == "female"
        cfg.build_weapons = a.only == "weapons" or True
    return cfg


# ----------------------------------------------------------------------------- weapon sets
def build_weapon_set(L, col, prefix: str = ""):
    """Build handgun, machine gun and kukri into ``col``; names are prefixed (unique per owner)."""
    pistol = weapons.build_pistol(L, col)
    rifle = weapons.build_rifle(L, col)
    kukri = weapons.build_kukri(L, col)
    act_names = weapons.animate_weapon_parts(pistol, rifle)
    if prefix:
        strip = lambda n: re.sub(r"\.\d{3}$", "", n)
        for w in (pistol, rifle, kukri):
            w["root"].name = prefix + strip(w["root"].name)
            for o in w["root"].children_recursive:
                o.name = prefix + strip(o.name)
        for n in act_names:
            a = bpy.data.actions.get(n)
            if a is not None:
                a.name = prefix + strip(n)
    return dict(handgun=pistol, machinegun=rifle, kukri=kukri), act_names


def push_part_actions(weapons_set):
    """Move object-level actions of weapon parts into NLA tracks so glTF export includes them."""
    for w in weapons_set.values():
        for o in w["parts"].values():
            ad = o.animation_data
            if ad is None or ad.action is None:
                continue
            act = ad.action
            tr = ad.nla_tracks.new()
            tr.name = act.name
            tr.strips.new(act.name, int(act.frame_range[0]), act)
            ad.action = None


def equip(arm, T, spec, wset, hand_weapon: str, holster: bool = True, back: str | None = None):
    """Attach demo weapons: one in the right hand, pistol holstered, kukri on left hip, optional rifle on back."""
    k = spec["scale"]
    bpy.context.view_layer.update()
    # hand-held
    wk = "rifle" if hand_weapon == "machinegun" else "pistol"
    w = animations.WEAPON[wk]
    Wr = rig.grip_rest_matrix(arm, T, "R", w["grip"], w["pitch"], w["right_shift"])
    rig.attach_to_bone(wset[hand_weapon]["root"], arm, "socket_weapon_R", Wr)
    # kukri (sheathed) on the left hip
    kuk = wset["kukri"]
    for part in ("blade", "handle"):
        kuk["parts"][part].location.x += weapons.KUKRI_SX
    frog = V((weapons.KUKRI_SX - 0.026, -0.14, 0.006))
    R = Matrix.Rotation(math.radians(78.0), 4, 'X') @ Matrix.Rotation(math.radians(-6.0), 4, 'Y')
    M = Matrix.Translation(T["socket_knife_L"]["head"] + V((0.012, 0.0, 0.0))) @ R @ Matrix.Translation(-frog)
    rig.attach_to_bone(kuk["root"], arm, "socket_knife_L", M)
    # holstered handgun (if not in hand) / slung rifle (if requested)
    if holster and hand_weapon != "handgun":
        hp = wset["handgun"]
        Mh = Matrix.Translation(T["socket_holster_R"]["head"] + V((-0.004, 0.0, 0.050 * k))) @ Matrix.Rotation(math.radians(90.0), 4, 'X')
        rig.attach_to_bone(hp["root"], arm, "socket_holster_R", Mh)
    if back and back != hand_weapon:
        rf = wset[back]
        Mb = Matrix.Translation(V((0.215 * k, 0.215 * k, 1.12 * k))) @ Matrix.Rotation(math.radians(-90.0), 4, 'X')
        rig.attach_to_bone(rf["root"], arm, "socket_back", Mb)


# ----------------------------------------------------------------------------- main build
def build(cfg: BuildConfig) -> dict:
    t0 = time.time()
    out: dict = dict(config=json.loads(cfg.to_json()), steps=[], files=[])
    log = lambda m: (print(f"[build {time.time() - t0:6.1f}s] {m}"), out["steps"].append(m))
    utils.clear_scene()
    sc = bpy.context.scene
    sc.render.fps = cfg.fps
    sc.frame_start, sc.frame_end = 1, 120
    m, f = CHARACTERS["male"], CHARACTERS["female"]
    L = materials.build_library(m["skin"], f["skin"], m["hair_color"], f["hair_color"])
    root = utils.get_collection("SH_Survival_Assets")
    built: dict = {}
    rep = validate.Report()
    export_objects: dict = {}          # name -> list of objects for per-asset glb
    pending_validation: list = []

    # ---- standalone weapons ------------------------------------------------------------------
    if cfg.build_weapons:
        wcol = utils.get_collection("Weapons", root)
        wset, _ = build_weapon_set(L, wcol, prefix="")
        for i, key in enumerate(("handgun", "machinegun", "kukri")):
            wset[key]["root"].location = (i * 1.2 - 1.2, 3.0, 0.0)
        push_part_actions(wset)
        built["weapons"] = wset
        log("weapons built: " + ", ".join(f"{k}:{len(v['parts'])} parts" for k, v in wset.items()))
        for key, w in wset.items():
            export_objects[f"weapon_{key}"] = [w["root"]] + list(w["root"].children_recursive)

    # ---- characters ----------------------------------------------------------------------------
    chars = []
    if cfg.build_male:
        chars.append("male")
    if cfg.build_female:
        chars.append("female")
    for ci, kind in enumerate(chars):
        spec = CHARACTERS[kind]
        nm = spec["name"]
        ch = character.build_character(kind, cfg, L, root)
        rig_col = utils.get_collection(f"{nm}_Rig", ch["collection"])
        eq_col = utils.get_collection(f"{nm}_Equipment", ch["collection"])
        arm = rig.create_armature(f"{nm}_Armature", ch["table"], rig_col)
        for o in ch["objects"].values():
            rig.bind_mesh(o, arm, cfg.skin_max_influences)
        keys = rig.add_face_shape_keys(ch["objects"]["head"], ch["head_info"], ch["female"])
        log(f"{nm}: {len(ch['objects'])} meshes, {len(ch['table'])} bones, shape keys {keys}")
        # equipment
        wset, _ = build_weapon_set(L, eq_col, prefix=f"{nm}_")
        if kind == "male":
            equip(arm, ch["table"], spec, wset, "machinegun", holster=True, back=None)
        else:
            equip(arm, ch["table"], spec, wset, "handgun", holster=False, back="machinegun")
        push_part_actions(wset)
        # animations
        names = animations.build_all_actions(arm, ch["table"], spec, cfg) if cfg.build_animations else []
        # prefix actions with the character name so both characters coexist
        for a in names:
            act = bpy.data.actions.get(a)
            if act is not None:
                act.name = f"{nm}_{a}"
        log(f"{nm}: actions {names}")
        # camera
        camrig = None
        if cfg.build_camera:
            cam_col = utils.get_collection(f"{nm}_Camera", ch["collection"])
            camrig = camera_rig.build_camera_rig(nm, cam_col, arm, sc, scale=spec["scale"])
        ch.update(armature=arm, weapons=wset, actions=names, camera=camrig)
        built[kind] = ch
        pending_validation.append(lambda ch=ch, arm=arm, names=names, wset=wset, nm=nm: (
            validate.validate_character(rep, ch, arm, names, cfg.skin_max_influences),
            validate.validate_weapons(rep, wset, label="")))
        objs = [arm] + list(ch["objects"].values())
        export_objects[f"character_{kind}"] = objs
        # place side by side
        off = (-1.0 if kind == "male" else 1.0)
        for o in [arm] + list(ch["objects"].values()) + [w["root"] for w in wset.values()]:
            if o.parent is None:
                o.location.x += off
        if camrig:
            camrig["pivot"].location = (0, 0, 0)

    if "weapons" in built:
        pending_validation.append(lambda: validate.validate_weapons(rep, built["weapons"]))
    # pose scene frame range from longest action
    try:
        longest = max(a.frame_range[1] for a in bpy.data.actions)
        sc.frame_end = int(longest)
    except ValueError:
        pass

    # ---- UV unwrap (non-overlapping smart projection, one UV set per mesh)
    nuv = 0
    for o in [o for o in bpy.data.objects if o.type == 'MESH']:
        if utils.unwrap_smart(o):
            nuv += 1
    log(f"UV unwrapped {nuv} meshes")

    for fn in pending_validation:
        fn()

    # ---- save procedural .blend --------------------------------------------------------------
    out_dir = cfg.output_dir
    os.makedirs(out_dir, exist_ok=True)
    blend_path = os.path.join(out_dir, "survival_horror_assets.blend")
    if cfg.export_blend:
        export.save_blend(blend_path)
        out["files"].append(blend_path)
        log(f"saved {blend_path}")

    # ---- bake + glb --------------------------------------------------------------------------
    glb_files = []
    if cfg.export_glb:
        table = {}
        if cfg.bake_textures:
            meshes = [o for o in bpy.data.objects if o.type == 'MESH']
            log(f"baking {len(meshes)} meshes @ {cfg.bake_resolution}px ...")
            table = bake.bake_objects(meshes, cfg.bake_resolution, cfg.bake_samples, os.path.join(out_dir, "textures"))
            log("baking finished")
        ctx = bake.swap_export_materials(table) if table else None
        try:
            if ctx:
                ctx.__enter__()
            if cfg.export_per_asset_glb:
                for key, objs in export_objects.items():
                    p = os.path.join(out_dir, "glb", f"{key}.glb")
                    export.export_glb(p, objs, animations=True)
                    glb_files.append(p)
                    log(f"exported {p}")
            p = os.path.join(out_dir, "glb", "survival_horror_scene.glb")
            export.export_glb(p, None, animations=True, cameras=True)
            glb_files.append(p)
            log(f"exported {p}")
        finally:
            if ctx:
                ctx.__exit__(None, None, None)
        if cfg.export_blend and cfg.bake_textures:
            # second save so that baked images are referenced from disk by the .blend as well
            export.save_blend(os.path.join(out_dir, "survival_horror_assets_baked_refs.blend"))
        out["files"].extend(glb_files)

    validate.check_exports(rep, out["files"])
    # ---- verify GLB by re-import (last: wipes the scene) ----------------------------------
    verify = {}
    for p in glb_files:
        try:
            verify[os.path.basename(p)] = validate.verify_glb(p)
        except Exception as exc:
            verify[os.path.basename(p)] = dict(error=str(exc))
    for name, v in verify.items():
        ok = "error" not in v and v.get("meshes", 0) > 0
        rep.add(f"glb re-import: {name}", ok, json.dumps({k: v[k] for k in v if k != 'action_names'}) if ok else str(v))
    out["glb_verify"] = verify
    out["validation"] = json.loads(rep.to_json())
    rp = os.path.join(out_dir, "validation_report.json")
    with open(rp, "w") as fh:
        json.dump(out, fh, indent=2, default=str)
    log(f"validation: {out['validation']['passed']} passed, {out['validation']['failed']} failed -> {rp}")
    for c in rep.failed:
        print("  FAILED:", c["name"], "|", c["detail"])
    return out


def main():
    cfg = parse_args()
    try:
        res = build(cfg)
    except Exception:
        traceback.print_exc()
        sys.exit(1)
    sys.exit(0 if res["validation"]["failed"] == 0 else 2)


if __name__ == "__main__":
    main()
