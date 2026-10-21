# Survival-horror asset generator (Blender / `bpy`)

Procedurally builds, rigs, animates, bakes and exports: **male + female character**, **handgun**, **machine gun (carbine)** and **kukri**
(with sheath, karda, chakmak). Deterministic (`--seed`), modular, validated.

## Run
```bash
# inside Blender 4.2+ (tested on 5.2.2 LTS via the PyPI `bpy` wheel)
blender --background --python build_all.py -- --out ./output
# or with the bpy wheel:  pip install bpy numpy && python build_all.py --out ./output
```
Options: `--no-bake` (skip textures), `--res 1024` (bake res), `--fast` (64-seg head, 512 px), `--only male|female|weapons`, `--seed N`.
Full build ≈ 6 min on 4 CPU cores (≈ 4.5 min is Cycles texture baking), ~3 GB RAM.
Previews: `python render_previews.py --blend output/survival_horror_assets.blend --out output/previews`.

## Layout
| module | purpose |
|---|---|
| `config.py` | `BuildConfig` + body / head dimension tables (`CHARACTERS`) – tweak proportions here |
| `utils.py` | `MeshBuilder` (bmesh wrapper: boxes, lofts, tubes, per-vertex skin weights, material slots), UV, modifiers |
| `materials.py` | 38 procedural PBR node materials (wear masks, weave, leather, diamond grip, digital camo, skin SSS, hair…) |
| `skeleton.py` | one bone table used for both weighting and the armature (49 bones male, 53 female incl. 4 ponytail bones) |
| `weapons.py` | handgun, carbine, kukri; separate moving parts (slide, trigger, bolt, magazine, charging handle) + `ATT_*` empties |
| `body.py`, `outfit.py`, `character.py` | skin, parametric head, eyes, brows, hair/beard/ponytail, jacket, shirt, pants, boots, gloves, harness, belt, pouches, holster, pads, backpack |
| `rig.py` | armature, weight clean-up (≤4 influences, normalised), 5 face shape keys, socket attachment |
| `animations.py` | FK/IK solver + 12 baked actions per character |
| `camera_rig.py` | pivot → boom → camera, driver-controlled, presets DEFAULT/AIM/CROUCH/SPRINT |
| `bake.py`, `export.py`, `validate.py` | node→image baking (colour, ORM, normal), `.blend` / `.glb` export, validation + GLB re-import test |

## What you get (`output/`)
* `survival_horror_assets.blend` – editable, **procedural** materials, collections per asset, characters with equipped weapons.
* `glb/` – `character_male/female.glb` (skinned, 5 morph targets, 12 animations), `weapon_*.glb`, `survival_horror_scene.glb` (everything + cameras). Textures baked (≤1024 px/material, ORM-packed, tangent normals).
* `validation_report.json` – 438 checks (objects, UVs, materials, vertex groups ⊆ bones, weights normalised, rig modifier, sockets, actions + key counts, exports, GLB re-import: skinned meshes / actions / shape keys survive).

Animations (per character, 30 fps): `Idle, Walk, Run, Crouch (enter+hold), Crouch_Walk, Sit (enter+hold), Aim_Rifle, Fire_Rifle, Reload_Rifle, Aim_Pistol, Fire_Pistol, Reload_Pistol`.
Poses are solved with a small analytic two-bone IK (feet planted, hands on the weapon grip / foregrip / magazine) and baked to plain quaternion keys – no constraints, so glTF keeps them.
Weapon parts carry their own actions (`*_Slide_Fire`, `*_Magazine_Reload`, `*_Bolt_Fire`, `*_ChargingHandle_Reload`, 96-frame reload shared with the characters).
Sockets (non-deform bones): `socket_weapon_R/L`, `socket_holster_R`, `socket_knife_L`, `socket_back`, `socket_camera_focus`.

## Honest limitations – what code cannot do (or does not do here)
1. **Facial likeness is NOT achieved.** The head is a landmark-driven parametric face (round broad face, heavy brow, wide nose, moustache + short beard for the male). It reads as "a bearded man with this costume", not as the person in the reference. A real likeness needs photogrammetry / FaceBuilder-style projection or hand sculpting (ZBrush/Blender sculpt) plus hand-painted skin textures. The same applies to skin pores, hair strands and micro-detail.
2. **No female reference image was supplied** (the 4th upload was a duplicate of the male sheet). She uses the same costume, female proportions, long high ponytail (4 spring-ready bones), **no earrings** (validated), generic face.
3. **No dedicated handgun reference** – modelled after the compact two-tone pistol in "Action Pose 1"; details are generic. The carbine and kukri follow their sheets closely in silhouette/parts, but are stylised game-res models, not scan-accurate.
4. Hair is mesh shell + clumps (no strand/hair-card alpha textures); cloth is skinned geometry, not simulated; folds/wrinkles are bump only.
5. Look: stylised mid-poly (male ≈ 65 k tris, female ≈ 78 k incl. hair; MG ≈ 35 k). It is *not* photoreal AAA; materials are procedural and baked at 1024 px per material.
6. Animations are procedural (clean but generic) – not mocap. Locomotion arms are FK (a held weapon swings loosely while walking/running); weapon-hand animations are `Aim/Fire/Reload`. The reload swaps the magazine object in place (no second magazine prop).
7. glTF does not store drivers/constraints: the camera rig's behaviour lives in the `.blend`; GLB gets the camera node at rest.
8. Procedural shaders are not exportable to glTF – they are baked (`bake.py`); the `.blend` keeps the editable procedural versions.
9. Facial shape keys are simple corrective shapes (jaw, smile, brows, squint), not a full FACS set; no eyelid blink geometry.

## Extending
Add a weapon: write `build_x(L, col)` in `weapons.py` returning `dict(root, parts)`, add an `ATT_Grip_R` empty and an entry in `animations.WEAPON`.
Change proportions: edit `config.CHARACTERS`; skeleton, meshes, IK and sockets follow automatically.
