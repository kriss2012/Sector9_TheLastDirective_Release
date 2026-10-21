"""Central configuration. Everything is deterministic given ``BuildConfig.seed``."""
from __future__ import annotations
from dataclasses import dataclass, field, asdict
import json, os


@dataclass
class BuildConfig:
    seed: int = 1337
    output_dir: str = "output"
    build_male: bool = True
    build_female: bool = True
    build_weapons: bool = True
    build_animations: bool = True
    build_camera: bool = True
    attach_demo_weapons: bool = True      # parent weapons to sockets in the character .blend
    bake_textures: bool = True            # needed for textured glTF (procedural nodes are not exported)
    bake_resolution: int = 1024           # per object / per material
    bake_samples: int = 1
    export_blend: bool = True
    export_glb: bool = True
    export_per_asset_glb: bool = True     # also export each character / weapon individually
    fps: int = 30
    render_previews: bool = False         # low-sample Cycles previews (slow, CPU only)
    preview_resolution: int = 768
    head_segments: int = 96               # head sphere resolution (u); v = 3/4 of this
    limb_sides: int = 16                  # ring vertex count for limbs / torso
    finger_sides: int = 8
    skin_max_influences: int = 4

    def to_json(self) -> str:
        return json.dumps(asdict(self), indent=2)

    def out(self, *parts: str) -> str:
        p = os.path.join(self.output_dir, *parts)
        os.makedirs(os.path.dirname(p) or ".", exist_ok=True)
        return p


# --------------------------------------------------------------------------------------
# Character body dimension tables (metres). Z up, character faces -Y, character's
# RIGHT side is -X (Blender front-view convention).
# --------------------------------------------------------------------------------------
CHARACTERS = {
    "male": dict(
        name="Male",
        height=1.80,
        scale=1.0,
        shoulder_half=0.205,      # clavicle tip x
        chest_w=0.205, chest_d=0.135,
        waist_w=0.178, waist_d=0.125,   # stocky build like the reference
        hip_w=0.185, hip_d=0.125,
        neck_r=0.062,
        thigh_r=0.098, calf_r=0.066, knee_r=0.062, ankle_r=0.042,
        upper_arm_r=0.050, forearm_r=0.042, wrist_r=0.030,
        hand_len=0.095, hand_w=0.045,
        foot_len=0.275,
        bust=0.0, glute=0.010,
        skin=(0.30, 0.145, 0.085), skin_sss=(0.8, 0.35, 0.2),
        hair_color=(0.012, 0.010, 0.010),
        head=dict(width=0.158, depth=0.205, height=0.232, jaw=1.05, cheek=1.0, brow=1.0,
                  nose_w=1.12, nose_len=1.0, lip=0.9, chin=1.0, forehead=1.0),
    ),
    "female": dict(
        name="Female",
        height=1.70,
        scale=0.945,
        shoulder_half=0.175,
        chest_w=0.165, chest_d=0.110,
        waist_w=0.125, waist_d=0.095,
        hip_w=0.172, hip_d=0.118,
        neck_r=0.044,
        thigh_r=0.090, calf_r=0.057, knee_r=0.052, ankle_r=0.035,
        upper_arm_r=0.039, forearm_r=0.034, wrist_r=0.024,
        hand_len=0.085, hand_w=0.039,
        foot_len=0.245,
        bust=0.030, glute=0.022,
        skin=(0.40, 0.215, 0.135), skin_sss=(0.8, 0.35, 0.2),
        hair_color=(0.016, 0.011, 0.009),
        head=dict(width=0.138, depth=0.190, height=0.222, jaw=0.82, cheek=0.95, brow=0.55,
                  nose_w=0.85, nose_len=0.92, lip=1.35, chin=0.85, forehead=1.0),
    ),
}

BODY_PARTS_SKIN_ONLY = ("body", "head")
