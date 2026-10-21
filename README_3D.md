# Sector9 — Third-Person Prototype (Panda3D)

Resident Evil–style TPP prototype: over-the-shoulder camera, WASD + mouse, walk / sprint /
crouch / sit / jump, pistol + carbine + kukri with aim, fire, reload, recoil, hit detection,
ammo and sound. Character and weapons are separate `.glb` assets; the arena in
`tps/testbed.py` is a throw-away you replace with your own environment.

## 1. Setup
```bash
pip install -r requirements-3d.txt        # panda3d + panda3d-gltf
# build the 3D assets with Blender (see tools/blender_assets/):
python tools/blender_assets/build_all.py --blender "<path-to-blender>" --out assets/models
python run_tps.py --selftest              # scripted control/weapon check, no window input needed
python run_tps.py                         # play
```
No Blender yet? `run_tps.py` falls back to placeholder boxes so you can test controls.
Sounds are generated into `assets/sfx/` on first run (drop in your own `.wav` with the same name to replace).

## 2. Controls
| Input | Action |
|---|---|
| W A S D | move (camera-relative) |
| Mouse | look / orbit camera |
| Shift | sprint (forward only, not while aiming/crouching) |
| C | toggle crouch (blocked if a ceiling is overhead) |
| X | toggle sit (only when standing still) |
| Space | jump (also stands up from crouch/sit) |
| Right mouse | aim (tighter spread, closer camera, character faces camera) |
| Left mouse | fire (pistol semi-auto, carbine full-auto) / kukri slash |
| R | reload (auto-reload on empty click) |
| 1 / 2 / 3 | pistol / carbine / kukri |
| Esc | release mouse (click to recapture) — F10 quits |

## 3. Layout
```
tps/physics.py     AABB collision, step-up, gravity, ray casts      (pure Python, tested)
tps/player.py      movement, stances, orbit camera + wall pull-in   (pure Python, tested)
tps/weapons.py     ammo, fire rate, reload, recoil, melee, switch   (pure Python, tested)
tps/anim_state.py  state -> rig action name                         (pure Python, tested)
tps/session.py     ties it together + hit resolution + targets      (pure Python, tested)
tps/sfx.py         procedural WAV generator                         (tested)
tps/testbed.py     placeholder arena  <-- replace with your level
tps/game.py        Panda3D rendering/input/audio front-end          (NOT yet run on real Panda3D)
tools/blender_assets/  Blender scripts that build character, rifle, pistol, kukri (.blend + .glb)
```
Tune speeds, camera and heights in `tps/config.py`, weapon stats in `tps/weapons.py`.

## 4. Verification status (be honest about what is proven)
| Area | Status |
|---|---|
| Logic: physics, movement, stances, weapons, recoil, reload, melee, hit detection, targets, anim selection, sfx files | **42 unit tests pass** — `python -m unittest tests.test_tps_logic -v` |
| `game.py` code paths (input -> session -> visuals -> HUD -> events) | executed end-to-end against a *stubbed* Panda3D only |
| Real rendering, glTF loading, skeletal animation playback, mouse capture, audio, shadows | **not yet run** — use `python run_tps.py --selftest` then play and report any traceback |
| Blender scripts | compile + stub-checked only; **not yet run in Blender** |
| Face likeness to the reference photos | **not achieved** — placeholder head; sculpt/photo-project later |

## 5. Things most likely to need a tweak on first run
* **Hand/weapon alignment**: weapons snap to the `Attach_HandR` bone position and take their heading from the
  aim direction. Nudge `HAND_OFFSET` in `tps/game.py` if the grip sits off the hand.
* **Animation names**: expects the 12 action names listed in `REQUIRED_ANIMS`; `--selftest` reports any missing.
* **Facing**: models face +Y. If the character walks backwards, rotate it 180° in `Sector9TPS._sync_visuals`.
* **Over-the-shoulder aiming**: shots leave along the camera ray (crosshair), not the muzzle — standard TPS behaviour.
