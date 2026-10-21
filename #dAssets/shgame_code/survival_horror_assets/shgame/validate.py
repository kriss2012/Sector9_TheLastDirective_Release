"""Post-build validation: objects, UVs, materials, rig assignments, animation actions, exports."""
from __future__ import annotations
import json
import os
from typing import Dict, List, Sequence

import bpy

REQUIRED_ACTIONS = ["Idle", "Walk", "Run", "Crouch", "Sit", "Aim_Rifle", "Fire_Rifle", "Reload_Rifle",
                    "Aim_Pistol", "Fire_Pistol", "Reload_Pistol"]
REQUIRED_SOCKETS = ["socket_weapon_R", "socket_weapon_L", "socket_holster_R", "socket_knife_L", "socket_back",
                    "socket_camera_focus"]


class Report:
    def __init__(self):
        self.checks: List[Dict] = []

    def add(self, name: str, ok: bool, detail: str = ""):
        self.checks.append(dict(name=name, ok=bool(ok), detail=detail))

    @property
    def failed(self):
        return [c for c in self.checks if not c["ok"]]

    def to_json(self):
        return json.dumps(dict(passed=len(self.checks) - len(self.failed), failed=len(self.failed), checks=self.checks), indent=2)


def validate_character(rep: Report, ch: Dict, arm: bpy.types.Object, action_names: Sequence[str], max_infl: int = 4):
    nm = ch["spec"]["name"]
    T = ch["table"]
    bones = {b.name for b in arm.data.bones}
    rep.add(f"{nm}: armature bone count", len(bones) == len(T), f"{len(bones)} bones")
    rep.add(f"{nm}: socket bones", all(s in bones for s in REQUIRED_SOCKETS), ",".join(s for s in REQUIRED_SOCKETS if s not in bones))
    if ch["female"]:
        rep.add(f"{nm}: ponytail bones", all(f"pony_{i}" in bones for i in (1, 2, 3, 4)))
        rep.add(f"{nm}: ponytail mesh present", any("ponytail" in o.name.lower() for o in ch["objects"].values()))
        bad = [o.name for o in bpy.data.objects if "earring" in o.name.lower() or "ring" == o.name.lower()[-4:] and nm in o.name]
        rep.add(f"{nm}: no earrings", not bad, ",".join(bad))
    tot_v = 0
    for key, o in ch["objects"].items():
        me = o.data
        tot_v += len(me.vertices)
        rep.add(f"{o.name}: UV map", len(me.uv_layers) > 0)
        rep.add(f"{o.name}: materials assigned", len(me.materials) > 0 and all(m is not None for m in me.materials))
        used = {p.material_index for p in me.polygons}
        rep.add(f"{o.name}: face material indices valid", all(i < len(me.materials) for i in used))
        mods = [m for m in o.modifiers if m.type == 'ARMATURE' and m.object == arm]
        rep.add(f"{o.name}: armature modifier", len(mods) == 1)
        rep.add(f"{o.name}: parented to armature", o.parent == arm)
        gnames = {g.name for g in o.vertex_groups}
        rep.add(f"{o.name}: vertex groups ⊆ bones", gnames <= bones, ",".join(sorted(gnames - bones)))
        # weights
        unweighted, over, unnorm = 0, 0, 0
        for v in me.vertices:
            gs = [g.weight for g in v.groups if g.weight > 1e-4]
            if not gs:
                unweighted += 1
            if len(gs) > max_infl:
                over += 1
            if gs and abs(sum(gs) - 1.0) > 0.01:
                unnorm += 1
        rep.add(f"{o.name}: all verts weighted", unweighted == 0, f"{unweighted} unweighted")
        rep.add(f"{o.name}: <= {max_infl} influences & normalised", over == 0 and unnorm == 0, f"over={over} unnorm={unnorm}")
    head = ch["objects"]["head"]
    rep.add(f"{nm}: face shape keys", head.data.shape_keys is not None and len(head.data.shape_keys.key_blocks) >= 4,
            str(len(head.data.shape_keys.key_blocks) if head.data.shape_keys else 0))
    # animations
    ad = arm.animation_data
    tracks = {t.name for t in ad.nla_tracks} if ad else set()
    for a in REQUIRED_ACTIONS:
        act = bpy.data.actions.get(f"{nm}_{a}") or bpy.data.actions.get(a)
        rep.add(f"{nm}: action {a}", a in tracks or f"{nm}_{a}" in tracks, "NLA track present" if a in tracks else "missing")
    for t in (ad.nla_tracks if ad else []):
        for s in t.strips:
            act = s.action
            nk = 0
            try:
                nk = sum(len(fc.keyframe_points) for fc in act.layers[0].strips[0].channelbags[0].fcurves)
            except Exception:
                try:
                    nk = sum(len(fc.keyframe_points) for fc in act.fcurves)
                except Exception:
                    nk = -1
            rep.add(f"{nm}: action '{act.name}' keyframes", nk != 0, f"{nk} keys, frames {act.frame_range[0]:.0f}-{act.frame_range[1]:.0f}")
    return tot_v


def validate_weapons(rep: Report, weapons: Dict[str, Dict], label: str = ""):
    for key, w in weapons.items():
        for pname, o in w["parts"].items():
            me = o.data
            rep.add(f"{label}{o.name}: has geometry", len(me.polygons) > 8, f"{len(me.polygons)} faces")
            rep.add(f"{label}{o.name}: UV map", len(me.uv_layers) > 0)
            rep.add(f"{label}{o.name}: materials", len(me.materials) > 0 and all(m is not None for m in me.materials))
        atts = [c.name for c in w["root"].children if "ATT_" in c.name]
        rep.add(f"{label}{key}: attachment points", len(atts) >= 3, ",".join(atts))


def check_exports(rep: Report, paths: Sequence[str]):
    for p in paths:
        rep.add(f"export exists: {os.path.basename(p)}", os.path.exists(p) and os.path.getsize(p) > 1024,
                f"{os.path.getsize(p) / 1e6:.2f} MB" if os.path.exists(p) else "missing")


def verify_glb(path: str) -> Dict:
    """Re-import the GLB into an empty scene and count what survived."""
    bpy.ops.wm.read_factory_settings(use_empty=True)
    try:
        bpy.ops.preferences.addon_enable(module='io_scene_gltf2')
    except Exception:
        pass
    bpy.ops.import_scene.gltf(filepath=path)
    meshes = [o for o in bpy.data.objects if o.type == 'MESH']
    arms = [o for o in bpy.data.objects if o.type == 'ARMATURE']
    skinned = [o for o in meshes if any(m.type == 'ARMATURE' for m in o.modifiers)]
    imgs = [i for i in bpy.data.images if i.size[0] > 0 and i.users > 0]
    return dict(meshes=len(meshes), armatures=len(arms), skinned_meshes=len(skinned), actions=len(bpy.data.actions),
                action_names=sorted(a.name for a in bpy.data.actions)[:60], images=len(imgs),
                shape_keys=sum(1 for o in meshes if o.data.shape_keys))
