"""Rigged third-person character: stocky male operator in black tactical jacket,
black shirt, chest/shoulder harness, utility belt with pouches, thigh holster,
cargo trousers with knee pads, combat boots, fingerless gloves, assault pack,
short dark hair and short beard (per reference sheet).

IMPORTANT: this is a procedural low/mid-poly body with a placeholder head. For
a true facial likeness, sculpt or photo-project onto the `Head` mesh afterwards
(the rig, outfit and attachment bones stay valid).

Skeleton: Hips > Spine > Chest > Neck > Head, UpperArm/LowerArm/Hand (.L/.R),
UpperLeg/LowerLeg/Foot (.L/.R) plus attachment bones for the game:
  Attach_HandR, Attach_HandL, Attach_Holster, Attach_Back, Attach_KukriBelt.
+Y = forward, +X = character's right (.R), height ~1.75 m.

blender --background --python tools/blender_assets/build_character.py -- --out assets/models
"""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *  # noqa: E402,F401,F403
from common import _finish  # noqa: E402

PARTS = []  # (object, bone_name) pairs skinned 100% to one bone


def reg(obj, bone):
    PARTS.append((obj, bone))
    return obj


def bx(name, size, loc, mat, bone, rot=(0, 0, 0), bevel=0.004):
    return reg(add_box(name, size, loc, mat, bevel, rot), bone)


def ell(name, loc, radii, mat, bone):
    return reg(add_sphere(name, 1.0, loc, mat, scale=radii), bone)


def seg(name, p0, p1, r0, r1, mat, bone, verts=20):
    """Tapered cylinder from p0 (radius r0) to p1 (radius r1) in any direction."""
    a, b = Vector(p0), Vector(p1)
    d = b - a
    rot = d.to_track_quat("Z", "Y").to_euler()
    bpy.ops.mesh.primitive_cone_add(vertices=verts, radius1=r0, radius2=r1, depth=d.length,
                                    location=(a + b) / 2, rotation=rot)
    return reg(_finish(bpy.context.active_object, name, mat, 0.0, None), bone)


# ------------------------------------------------------------------- skeleton
def make_armature():
    bpy.ops.object.armature_add(enter_editmode=True, location=(0, 0, 0))
    arm = bpy.context.active_object
    arm.name = "Armature"
    arm.data.name = "Armature"
    eb = arm.data.edit_bones
    for b in list(eb):
        eb.remove(b)

    def bone(name, head, tail, parent=None):
        b = eb.new(name)
        b.head, b.tail = head, tail
        if parent:
            b.parent = eb[parent]
        return b

    bone("Hips", (0, 0, 0.98), (0, 0, 1.08))
    bone("Spine", (0, 0, 1.08), (0, 0, 1.28), "Hips")
    bone("Chest", (0, 0, 1.28), (0, 0, 1.45), "Spine")
    bone("Neck", (0, 0, 1.45), (0, 0.01, 1.52), "Chest")
    bone("Head", (0, 0.01, 1.52), (0, 0.01, 1.76), "Neck")
    for s, sx in (("R", 1), ("L", -1)):
        bone(f"UpperArm.{s}", (sx * 0.21, 0, 1.42), (sx * 0.23, 0, 1.15), "Chest")
        bone(f"LowerArm.{s}", (sx * 0.23, 0, 1.15), (sx * 0.24, 0, 0.90), f"UpperArm.{s}")
        bone(f"Hand.{s}", (sx * 0.24, 0, 0.90), (sx * 0.24, 0, 0.79), f"LowerArm.{s}")
        bone(f"UpperLeg.{s}", (sx * 0.10, 0, 0.95), (sx * 0.10, 0, 0.53), "Hips")
        bone(f"LowerLeg.{s}", (sx * 0.10, 0, 0.53), (sx * 0.10, 0, 0.10), f"UpperLeg.{s}")
        bone(f"Foot.{s}", (sx * 0.10, 0, 0.10), (sx * 0.10, 0.15, 0.05), f"LowerLeg.{s}")
    # Attachment points (weapons/props parent to these in the game)
    bone("Attach_HandR", (0.24, 0.03, 0.84), (0.24, 0.10, 0.84), "Hand.R")
    bone("Attach_HandL", (-0.24, 0.03, 0.84), (-0.24, 0.10, 0.84), "Hand.L")
    bone("Attach_Holster", (0.20, 0.0, 0.80), (0.20, 0.0, 0.70), "UpperLeg.R")
    bone("Attach_Back", (0, -0.17, 1.30), (0, -0.17, 1.40), "Chest")
    bone("Attach_KukriBelt", (-0.18, 0.02, 1.02), (-0.18, 0.02, 0.92), "Hips")
    bpy.ops.object.mode_set(mode="OBJECT")
    return arm


# ----------------------------------------------------------------------- body
def build_body(M):
    jk, sh, sk, hr = M["jacket"], M["shirt"], M["skin"], M["hair"]
    # Torso (shirt) + jacket shells (open front) + collar
    ell("Pelvis", (0, 0, 1.00), (0.185, 0.115, 0.13), M["pants"], "Hips")
    ell("Abdomen", (0, 0, 1.15), (0.175, 0.110, 0.15), sh, "Spine")
    ell("ChestShirt", (0, 0, 1.31), (0.195, 0.120, 0.20), sh, "Chest")
    for s, sx in (("R", 1), ("L", -1)):
        bx(f"JacketFront.{s}", (0.130, 0.250, 0.40), (sx * 0.125, 0.0, 1.27), jk, "Chest", bevel=0.012)
        bx(f"JacketHem.{s}", (0.130, 0.240, 0.12), (sx * 0.120, 0.0, 1.03), jk, "Spine", bevel=0.01)
        bx(f"Collar.{s}", (0.040, 0.200, 0.080), (sx * 0.075, 0.0, 1.49), jk, "Chest", bevel=0.01)
        ell(f"Shoulder.{s}", (sx * 0.215, 0, 1.40), (0.075, 0.075, 0.075), jk, f"UpperArm.{s}")
        # Harness straps over shoulders to belt + shoulder patch
        bx(f"Strap.{s}", (0.045, 0.012, 0.46), (sx * 0.095, 0.130, 1.27), M["strap"], "Chest",
           rot=(0, math.radians(sx * 4), 0), bevel=0.003)
        bx(f"StrapBack.{s}", (0.045, 0.012, 0.46), (sx * 0.095, -0.130, 1.27), M["strap"], "Chest")
        bx(f"Patch.{s}", (0.012, 0.075, 0.085), (sx * 0.292, 0, 1.30), M["strap"], f"UpperArm.{s}")
    bx("ChestBuckle", (0.090, 0.018, 0.045), (0, 0.128, 1.30), M["metal"], "Chest")
    bx("ChestStrapH", (0.200, 0.014, 0.035), (0, 0.126, 1.30), M["strap"], "Chest")
    bx("Zipper", (0.006, 0.012, 0.40), (0, 0.128, 1.27), M["metal"], "Chest", bevel=0.001)
    # Belt, buckle, pouches
    ell("Belt", (0, 0, 1.03), (0.205, 0.140, 0.035), M["strap"], "Hips")
    bx("BeltBuckle", (0.060, 0.020, 0.045), (0, 0.140, 1.03), M["metal"], "Hips")
    for i, (px, py) in enumerate([(0.12, 0.125), (-0.12, 0.125), (0.205, 0.04), (-0.205, 0.04), (0.0, -0.14)]):
        bx(f"Pouch{i}", (0.060, 0.045, 0.085), (px, py, 1.00), M["pouch"], "Hips", bevel=0.006)
        bx(f"PouchFlap{i}", (0.062, 0.048, 0.025), (px, py, 1.045), M["pouch"], "Hips", bevel=0.004)
    # Neck + head (placeholder head: see module docstring)
    seg("Neck", (0, 0, 1.46), (0, 0.01, 1.56), 0.062, 0.055, sk, "Neck")
    ell("Head", (0, 0.012, 1.655), (0.092, 0.108, 0.118), sk, "Head")
    ell("Jaw", (0, 0.035, 1.600), (0.082, 0.085, 0.070), sk, "Head")
    ell("Hair", (0, -0.005, 1.700), (0.098, 0.112, 0.092), hr, "Head")
    bx("Fringe", (0.150, 0.040, 0.040), (0, 0.090, 1.735), hr, "Head", rot=(math.radians(-15), 0, 0), bevel=0.01)
    ell("Beard", (0, 0.062, 1.585), (0.078, 0.060, 0.055), M["beard"], "Head")
    bx("Moustache", (0.060, 0.020, 0.014), (0, 0.108, 1.622), M["beard"], "Head", bevel=0.004)
    bx("Nose", (0.026, 0.030, 0.046), (0, 0.112, 1.650), sk, "Head", rot=(math.radians(-12), 0, 0), bevel=0.008)
    for s, sx in (("R", 1), ("L", -1)):
        ell(f"Ear.{s}", (sx * 0.094, 0.005, 1.650), (0.012, 0.028, 0.040), sk, "Head")
        ell(f"Eye.{s}", (sx * 0.036, 0.100, 1.672), (0.014, 0.008, 0.009), M["eye"], "Head")
        bx(f"Brow.{s}", (0.040, 0.012, 0.010), (sx * 0.038, 0.102, 1.692), hr, "Head", bevel=0.003)
    # Arms: jacket sleeve (rolled), bare forearm, gloves, watch (left wrist)
    for s, sx in (("R", 1), ("L", -1)):
        seg(f"Sleeve.{s}", (sx * 0.215, 0, 1.40), (sx * 0.235, 0, 1.12), 0.075, 0.068, jk, f"UpperArm.{s}")
        ell(f"Elbow.{s}", (sx * 0.235, 0, 1.15), (0.075, 0.075, 0.075), jk, f"UpperArm.{s}")
        seg(f"Cuff.{s}", (sx * 0.235, 0, 1.14), (sx * 0.240, 0, 1.04), 0.070, 0.066, jk, f"LowerArm.{s}")
        seg(f"Forearm.{s}", (sx * 0.240, 0, 1.04), (sx * 0.245, 0, 0.88), 0.060, 0.045, sk, f"LowerArm.{s}")
        seg(f"Glove.{s}", (sx * 0.245, 0, 0.905), (sx * 0.245, 0, 0.86), 0.052, 0.050, M["glove"], f"Hand.{s}")
        ell(f"Palm.{s}", (sx * 0.245, 0.012, 0.825), (0.050, 0.032, 0.062), M["glove"], f"Hand.{s}")
        for f in range(4):
            seg(f"Finger.{s}{f}", (sx * (0.222 + f * 0.015), 0.018, 0.790), (sx * (0.222 + f * 0.015), 0.022, 0.745),
                0.0095, 0.0085, M["glove"], f"Hand.{s}", verts=8)
        seg(f"Thumb.{s}", (sx * 0.205, 0.020, 0.830), (sx * 0.200, 0.050, 0.790), 0.012, 0.010, M["glove"],
            f"Hand.{s}", verts=8)
    bx("Watch", (0.062, 0.062, 0.016), (-0.246, 0.0, 0.915), M["metal"], "Hand.L", bevel=0.004)
    # Legs: trousers, knee pads, cargo pockets, thigh holster, boots
    for s, sx in (("R", 1), ("L", -1)):
        seg(f"Thigh.{s}", (sx * 0.10, 0, 0.98), (sx * 0.10, 0, 0.53), 0.105, 0.078, M["pants"], f"UpperLeg.{s}")
        ell(f"KneeJoint.{s}", (sx * 0.10, 0, 0.53), (0.080, 0.080, 0.080), M["pants"], f"UpperLeg.{s}")
        seg(f"Shin.{s}", (sx * 0.10, 0, 0.53), (sx * 0.10, 0, 0.17), 0.078, 0.062, M["pants"], f"LowerLeg.{s}")
        ell(f"KneePad.{s}", (sx * 0.10, 0.065, 0.54), (0.062, 0.030, 0.062), M["pad"], f"LowerLeg.{s}")
        bx(f"CargoPocket.{s}", (0.040, 0.090, 0.120), (sx * 0.185, 0.0, 0.74), M["pants"], f"UpperLeg.{s}", bevel=0.008)
        seg(f"BootShaft.{s}", (sx * 0.10, 0, 0.255), (sx * 0.10, 0, 0.06), 0.075, 0.070, M["boot"], f"LowerLeg.{s}")
        bx(f"BootFoot.{s}", (0.105, 0.280, 0.095), (sx * 0.10, 0.065, 0.065), M["boot"], f"Foot.{s}", bevel=0.02)
        bx(f"BootSole.{s}", (0.112, 0.295, 0.030), (sx * 0.10, 0.068, 0.015), M["sole"], f"Foot.{s}", bevel=0.006)
    bx("HolsterBody", (0.040, 0.075, 0.150), (0.185, 0.015, 0.70), M["pouch"], "UpperLeg.R", bevel=0.008)
    bx("HolsterStrap", (0.050, 0.085, 0.020), (0.185, 0.015, 0.78), M["strap"], "UpperLeg.R", bevel=0.003)
    bx("LegStrap", (0.090, 0.095, 0.020), (0.10, 0.0, 0.62), M["strap"], "UpperLeg.R", bevel=0.003)
    # Assault pack
    bx("Pack", (0.300, 0.170, 0.400), (0, -0.170, 1.28), M["pack"], "Chest", bevel=0.02)
    for s, sx in (("R", 1), ("L", -1)):
        bx(f"PackPocket.{s}", (0.120, 0.060, 0.220), (sx * 0.085, -0.275, 1.22), M["pack"], "Chest", bevel=0.012)
    bx("PackTop", (0.280, 0.150, 0.050), (0, -0.170, 1.50), M["pack"], "Chest", bevel=0.01)


def skin_parts(arm):
    """Bake bevels, then weight each part 100% to its bone (armature modifier)."""
    for obj, bone in PARTS:
        bpy.context.view_layer.objects.active = obj
        for mod in list(obj.modifiers):
            bpy.ops.object.modifier_apply(modifier=mod.name)
        vg = obj.vertex_groups.new(name=bone)
        vg.add(list(range(len(obj.data.vertices))), 1.0, "REPLACE")
        am = obj.modifiers.new("Armature", "ARMATURE")
        am.object = arm
        obj.parent = arm


def build():
    clear_scene()
    M = {
        "jacket": make_material("JacketBlack", (0.025, 0.025, 0.028), 0.0, 0.80),
        "shirt": make_material("ShirtBlack", (0.015, 0.015, 0.018), 0.0, 0.85),
        "pants": make_material("PantsBlack", (0.030, 0.030, 0.032), 0.0, 0.85),
        "skin": make_material("Skin", (0.50, 0.34, 0.25), 0.0, 0.55),
        "hair": make_material("Hair", (0.012, 0.010, 0.010), 0.0, 0.50),
        "beard": make_material("Beard", (0.02, 0.016, 0.014), 0.0, 0.60),
        "eye": make_material("Eye", (0.02, 0.012, 0.008), 0.0, 0.2),
        "glove": make_material("GloveLeather", (0.020, 0.020, 0.022), 0.0, 0.60),
        "strap": make_material("StrapWebbing", (0.040, 0.040, 0.045), 0.0, 0.90),
        "pouch": make_material("PouchNylon", (0.035, 0.032, 0.030), 0.0, 0.80),
        "metal": make_material("BuckleMetal", (0.12, 0.12, 0.13), 1.0, 0.35),
        "pad": make_material("KneePad", (0.020, 0.020, 0.022), 0.0, 0.50),
        "boot": make_material("BootLeather", (0.012, 0.012, 0.014), 0.0, 0.45),
        "sole": make_material("BootSole", (0.006, 0.006, 0.007), 0.0, 0.70),
        "pack": make_material("PackFabric", (0.030, 0.030, 0.032), 0.0, 0.85),
    }
    root = make_root("Character")
    arm = make_armature()
    arm.parent = root
    build_body(M)
    skin_parts(arm)
    return root, arm


if __name__ == "__main__":
    out = parse_out_dir()
    root, arm = build()
    from build_animations import add_animations
    print("[Sector9] actions:", add_animations(arm))
    try:  # Blender 3.6+ / 4.x
        export_asset(root, out, "character_operator", apply_mods=False,
                     export_animations=True, export_animation_mode="NLA_TRACKS")
    except TypeError:  # older Blender
        export_asset(root, out, "character_operator", apply_mods=False,
                     export_animations=True, export_nla_strips=True)
