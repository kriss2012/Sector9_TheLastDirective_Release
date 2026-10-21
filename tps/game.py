"""Panda3D front-end for the Sector9 third-person prototype.

All gameplay rules live in session.py (unit-tested). This file only: reads input,
steps the session, positions the camera/character/weapons, blends rig animations,
plays sounds and draws the HUD.  Run with:  python run_tps.py
"""
import math
import os
import sys

from direct.actor.Actor import Actor
from direct.gui.OnscreenText import OnscreenText
from direct.showbase.ShowBase import ShowBase
from panda3d.core import (AmbientLight, AntialiasAttrib, CardMaker, ClockObject, DirectionalLight, Filename, Fog, LineSegs,
                          ModifierButtons, TextNode, WindowProperties, loadPrcFileData)

from . import config as C
from .anim_state import ONE_SHOT, pick_animation
from .session import FrameInput, GameSession
from .sfx import generate_all

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODEL_DIR = os.path.join(ROOT, "assets", "models")
SFX_DIR = os.path.join(ROOT, "assets", "sfx")
REQUIRED_ANIMS = {"idle", "walk", "sprint", "crouch_idle", "crouch_walk", "sit", "jump", "aim_pistol",
                  "aim_rifle", "reload_pistol", "reload_rifle", "melee_slash"}
WEAPON_FILES = {"pistol": "pistol_m1911.glb", "rifle": "rifle_carbine.glb", "kukri": "knife_kukri.glb"}
HAND_OFFSET = (0.0, 0.0, 0.0)     # extra offset from the hand bone to the weapon grip (character space)
FADE_TIME = 0.18


def _pp(path):
    return str(Filename.fromOsSpecific(path))


class Sector9TPS(ShowBase):
    def __init__(self, selftest=False, shadows=True, seed=None):
        loadPrcFileData("", "window-title Sector9 - Third Person Prototype")
        loadPrcFileData("", "framebuffer-multisample 1\nmultisamples 4\nsync-video 1")
        if selftest:
            loadPrcFileData("", "window-type offscreen\naudio-library-name null")
        super().__init__()
        self.selftest = selftest
        try:                                   # panda3d-gltf: harmless if auto-registered
            import gltf
            gltf.patch_loader(self.loader)
        except Exception:
            pass
        self.disableMouse()
        self._clock = ClockObject.getGlobalClock()
        self.session = GameSession(seed=seed)
        self.keys = {}
        self.edges = set()
        self.mouse = {"fire": False, "aim": False}
        self.captured = False
        self.cur_anim, self.prev_anim, self.fade_t = None, None, 1.0
        self.step_timer = 0.0
        self.log = []
        self._build_scene(shadows)
        self._load_character()
        self._load_weapons()
        self._load_sfx()
        self._build_hud()
        self._setup_input()
        self.taskMgr.add(self._tick, "tick")

    # =============================================================== scene
    def _box_node(self, lo, hi, color, name):
        m = self.loader.loadModel("models/box")
        a, b = m.getTightBounds()
        size = b - a
        s = [(hi[i] - lo[i]) / max(1e-6, size[i]) for i in range(3)]
        m.setScale(*s)
        m.setPos(lo[0] - a[0] * s[0], lo[1] - a[1] * s[1], lo[2] - a[2] * s[2])
        m.setColor(*color)
        m.setName(name)
        m.reparentTo(self.render)
        return m

    def _build_scene(self, shadows):
        self.setBackgroundColor(0.04, 0.06, 0.09, 1)
        fog = Fog("fog")
        fog.setColor(0.04, 0.06, 0.09)
        fog.setExpDensity(0.012)
        self.render.setFog(fog)
        cm = CardMaker("ground")
        cm.setFrame(-60, 60, -60, 60)
        ground = self.render.attachNewNode(cm.generate())
        ground.setP(-90)
        ground.setColor(0.17, 0.18, 0.19, 1)
        grid = LineSegs()
        grid.setColor(0.28, 0.30, 0.32, 1)
        for i in range(-60, 61, 2):
            grid.moveTo(i, -60, 0.01); grid.drawTo(i, 60, 0.01)
            grid.moveTo(-60, i, 0.01); grid.drawTo(60, i, 0.01)
        self.render.attachNewNode(grid.create())
        amb = AmbientLight("amb")
        amb.setColor((0.28, 0.30, 0.36, 1))
        self.render.setLight(self.render.attachNewNode(amb))
        sun = DirectionalLight("sun")
        sun.setColor((1.0, 0.93, 0.80, 1))
        if shadows:
            sun.setShadowCaster(True, 2048, 2048)
            sun.getLens().setFilmSize(70, 70)
            sun.getLens().setNearFar(5, 120)
        self.sun_np = self.render.attachNewNode(sun)
        self.sun_np.setPos(25, -25, 45)
        self.sun_np.lookAt(0, 0, 0)
        self.render.setLight(self.sun_np)
        self.render.setShaderAuto()
        self.render.setAntialias(AntialiasAttrib.MAuto)
        self.box_nodes = {}
        for b in self.session.world.boxes:
            col = self.session.colors.get(b.name, (0.4, 0.4, 0.4, 1))
            self.box_nodes[b.name] = (b, self._box_node(b.lo, b.hi, col, b.name), col)

    # ============================================================= character
    def _load_character(self):
        self.actor, self.anims, self.hand_r = None, set(), None
        path = os.path.join(MODEL_DIR, "character_operator.glb")
        if os.path.exists(path):
            self.actor = Actor(_pp(path))
            self.actor.reparentTo(self.render)
            self.anims = set(self.actor.getAnimNames())
            self.actor.enableBlend()
            self.hand_r = self.actor.exposeJoint(None, "modelRoot", "Attach_HandR")
            self.char = self.actor
            missing = REQUIRED_ANIMS - self.anims
            if missing:
                print("[Sector9] WARNING missing animations:", sorted(missing))
        else:
            print("[Sector9] character_operator.glb not found in assets/models - using placeholder box.")
            self.char = self.render.attachNewNode("placeholder_char")
            self._box_node((-0.25, -0.15, 0.0), (0.25, 0.15, 1.75), (0.1, 0.1, 0.12, 1), "ph").reparentTo(self.char)

    def _load_weapons(self):
        self.weapon_nodes = {}
        for key, fname in WEAPON_FILES.items():
            path = os.path.join(MODEL_DIR, fname)
            if os.path.exists(path):
                node = self.loader.loadModel(_pp(path))
                node.reparentTo(self.render)
            else:
                node = self.render.attachNewNode("ph_" + key)
                length = {"pistol": 0.22, "rifle": 0.9, "kukri": 0.45}[key]
                self._box_node((-0.02, -0.05, -0.04), (0.02, length, 0.06), (0.15, 0.15, 0.17, 1), key).reparentTo(node)
            node.hide()
            self.weapon_nodes[key] = node

    # ================================================================ audio
    def _load_sfx(self):
        generate_all(SFX_DIR)                  # only creates missing files
        self.sfx = {}
        for fn in os.listdir(SFX_DIR):
            if fn.endswith(".wav"):
                pool = [self.loader.loadSfx(_pp(os.path.join(SFX_DIR, fn))) for _ in range(3)]
                self.sfx[fn[:-4]] = [0, pool]

    def play(self, name, volume=0.8, rate=1.0):
        entry = self.sfx.get(name)
        if not entry:
            return
        entry[0] = (entry[0] + 1) % len(entry[1])
        snd = entry[1][entry[0]]
        snd.setVolume(volume)
        snd.setPlayRate(rate)
        snd.play()

    # ================================================================== HUD
    def _build_hud(self):
        kw = dict(fg=(0.9, 0.95, 1, 1), shadow=(0, 0, 0, 0.8), mayChange=True)
        self.hud_ammo = OnscreenText(text="", pos=(1.28, -0.9), scale=0.09, align=TextNode.ARight, **kw)
        self.hud_weapon = OnscreenText(text="", pos=(1.28, -0.80), scale=0.055, align=TextNode.ARight, **kw)
        self.hud_state = OnscreenText(text="", pos=(-1.30, -0.9), scale=0.05, align=TextNode.ALeft, **kw)
        self.hud_cross = OnscreenText(text="+", pos=(0, -0.02), scale=0.07, **kw)
        self.hud_hit = OnscreenText(text="", pos=(0, -0.02), scale=0.09, fg=(1, 0.2, 0.2, 1), mayChange=True)
        self.hud_help = OnscreenText(
            text="WASD move | Mouse look | Shift sprint | C crouch | X sit | Space jump | RMB aim | LMB fire/slash\n"
                 "1 Pistol  2 Carbine  3 Kukri | R reload | Esc release mouse (click to recapture) | F10 quit",
            pos=(-1.30, 0.93), scale=0.04, align=TextNode.ALeft, **kw)
        self.hit_timer = 0.0

    # ================================================================ input
    def _setup_input(self):
        self.buttonThrowers[0].node().setModifierButtons(ModifierButtons())   # no 'shift-w' style events
        for k in ("w", "a", "s", "d", "lshift", "rshift"):
            self.accept(k, self.keys.__setitem__, [k, True])
            self.accept(k + "-up", self.keys.__setitem__, [k, False])
        for k in ("space", "c", "x", "r", "1", "2", "3"):
            self.accept(k, self.edges.add, [k])
        self.accept("mouse1", self._mouse, ["fire", True])
        self.accept("mouse1-up", self._mouse, ["fire", False])
        self.accept("mouse3", self._mouse, ["aim", True])
        self.accept("mouse3-up", self._mouse, ["aim", False])
        self.accept("escape", self._set_capture, [False])
        self.accept("f10", sys.exit)
        self._set_capture(True)

    def _mouse(self, which, state):
        self.mouse[which] = state
        if state and not self.captured:
            self._set_capture(True)

    def _set_capture(self, on):
        self.captured = on
        props = WindowProperties()
        props.setCursorHidden(on)
        props.setMouseMode(WindowProperties.M_confined if on else WindowProperties.M_absolute)
        self.win.requestProperties(props)
        if on and not self.selftest:
            self._center()

    def _center(self):
        self.cx, self.cy = self.win.getXSize() // 2, self.win.getYSize() // 2
        self.win.movePointer(0, self.cx, self.cy)

    def _read_mouse(self):
        if not self.captured or self.selftest or not self.mouseWatcherNode.hasMouse():
            return 0.0, 0.0
        p = self.win.getPointer(0)
        dx, dy = p.getX() - self.cx, p.getY() - self.cy
        self.win.movePointer(0, self.cx, self.cy)
        return float(dx), float(dy)

    def _gather_input(self):
        k, e = self.keys, self.edges
        dx, dy = self._read_mouse()
        fi = FrameInput(
            move_x=float(k.get("d", False)) - float(k.get("a", False)),
            move_y=float(k.get("w", False)) - float(k.get("s", False)),
            look_dx=dx, look_dy=dy,
            sprint=bool(k.get("lshift") or k.get("rshift")),
            aim=self.mouse["aim"], fire=self.mouse["fire"] and self.captured,
            jump="space" in e, toggle_crouch="c" in e, toggle_sit="x" in e, reload="r" in e,
            switch_to={"1": 0, "2": 1, "3": 2}.get(next((s for s in ("1", "2", "3") if s in e), ""), None))
        e.clear()
        return fi

    # ================================================================= frame
    def _tick(self, task):
        if not self.selftest:
            self.step_frame(min(self._clock.getDt(), 0.05), self._gather_input())
        return task.cont

    def step_frame(self, dt, fi):
        ev = self.session.update(dt, fi)
        self._handle_events(ev)
        self._sync_visuals(dt)
        return ev

    # ----------------------------------------------------------------- events
    def _handle_events(self, events):
        w = self.session.weapons
        for e in events:
            self.log.append(e)
            kind = e[0]
            if kind == "fire":
                self.play("pistol_fire" if w.wdef.key == "pistol" else "rifle_fire", 0.9)
            elif kind == "dry":
                self.play("dry_click")
            elif kind == "reload_start":
                self.play("reload_start")
            elif kind == "reload_end":
                self.play("reload_end")
            elif kind == "switch":
                self.play("switch")
            elif kind == "melee":
                self.play("melee_swing")
            elif kind == "jump":
                self.play("jump", 0.5)
            elif kind == "land":
                self.play("land", 0.6)
            elif kind == "hit":
                self.play("melee_hit" if w.wdef.kind == "melee" else "hit_marker", 0.7)
                self.hud_hit.setText("x")
                self.hit_timer = 0.15
                node = self.box_nodes.get(e[1])
                if node:
                    node[1].setColor(1, 1, 1, 1)
            elif kind == "destroyed":
                self.play("target_down")
            elif kind == "tracer":
                self._tracer(e[2])
            elif kind == "impact":
                self._marker(e[1])
                self.play("impact", 0.35)

    def _muzzle_pos(self):
        node = self.weapon_nodes[self.session.weapons.wdef.key]
        return self.render.getRelativePoint(node, (0, 0.6 if self.session.weapons.wdef.key == "rifle" else 0.2, 0.05))

    def _tracer(self, end):
        if self.session.weapons.wdef.kind != "ranged":
            return
        ls = LineSegs()
        ls.setColor(1, 0.85, 0.4, 1)
        ls.setThickness(2)
        ls.moveTo(self._muzzle_pos())
        ls.drawTo(*end)
        np = self.render.attachNewNode(ls.create())
        np.setLightOff()
        self.taskMgr.doMethodLater(0.05, lambda t: (np.removeNode(), t.done)[1], "rm_tracer")

    def _marker(self, p):
        m = self._box_node((p[0] - 0.04, p[1] - 0.04, p[2] - 0.04), (p[0] + 0.04, p[1] + 0.04, p[2] + 0.04),
                           (1.0, 0.6, 0.1, 1), "impact")
        m.setLightOff()
        self.taskMgr.doMethodLater(0.3, lambda t: (m.removeNode(), t.done)[1], "rm_marker")

    # ---------------------------------------------------------------- visuals
    def _sync_visuals(self, dt):
        s = self.session
        p, wsys = s.player, s.weapons
        # camera
        pos, h, pitch = p.camera_transform()
        self.camera.setPos(*pos)
        self.camera.setHpr(h, pitch, 0)
        target_fov = C.FOV_AIM if p.aiming else C.FOV_NORMAL
        cur = self.camLens.getFov()[0]
        self.camLens.setFov(cur + (target_fov - cur) * min(1.0, 10 * dt))
        # character
        self.char.setPos(p.body.x, p.body.y, p.body.z)
        self.char.setH(math.degrees(p.face_yaw))
        self._animate(dt)
        self._place_weapon()
        self._footsteps(dt)
        # targets
        for name, (box, node, col) in self.box_nodes.items():
            if box.hp is not None:
                if box.dead:
                    node.hide()
                else:
                    node.show()
                    c = node.getColor()
                    node.setColor(c[0] + (col[0] - c[0]) * min(1, 8 * dt), c[1] + (col[1] - c[1]) * min(1, 8 * dt),
                                  c[2] + (col[2] - c[2]) * min(1, 8 * dt), 1)
        # HUD
        slot = wsys.slot
        if wsys.wdef.kind == "ranged":
            self.hud_ammo.setText(f"{slot.ammo} / {slot.reserve}" + ("  RELOADING" if wsys.reloading else ""))
        else:
            self.hud_ammo.setText("")
        self.hud_weapon.setText(wsys.wdef.name)
        self.hud_state.setText(f"{p.stance.upper()}  {'SPRINT' if p.sprinting else ''}  "
                               f"{'AIM' if p.aiming else ''}  FPS {self._clock.getAverageFrameRate():.0f}")
        self.hud_cross.setText("." if p.aiming else "+")
        self.hit_timer -= dt
        if self.hit_timer <= 0:
            self.hud_hit.setText("")

    def _place_weapon(self):
        s = self.session
        p, w = s.player, s.weapons
        key = w.wdef.key
        for k, n in self.weapon_nodes.items():
            n.show() if k == key else n.hide()
        node = self.weapon_nodes[key]
        if self.hand_r is not None:
            hp = self.hand_r.getPos(self.render)
        else:
            hp = self.render.getRelativePoint(self.char, (0.24, 0.1, 0.9))
        off = self.render.getRelativeVector(self.char, HAND_OFFSET)
        node.setPos(hp + off)
        if w.wdef.kind == "ranged":
            yaw = (p.cam_yaw + p.recoil_yaw) if p.aiming else p.face_yaw
            pitch = math.degrees(p.cam_pitch + p.recoil_pitch) if p.aiming else -5.0
            node.setHpr(math.degrees(yaw), pitch, 0)
        else:
            prog = 1.0 - w.melee_left / w.wdef.melee_time if w.melee_left > 0 else 0.0
            sweep = 55 - 125 * min(1.0, prog * 1.4) if w.melee_left > 0 else 0.0
            node.setHpr(math.degrees(p.face_yaw) + sweep, -15, 0)

    def _footsteps(self, dt):
        p = self.session.player
        if p.body.on_ground and p.moving and p.stance != "sit":
            self.step_timer -= dt
            if self.step_timer <= 0:
                self.play("footstep", 0.25 if p.stance == "crouch" else 0.5, 1.0 + (0.15 if p.sprinting else 0))
                self.step_timer = 0.28 if p.sprinting else (0.7 if p.stance == "crouch" else 0.48)
        else:
            self.step_timer = 0.0

    # --------------------------------------------------------------- animation
    def _animate(self, dt):
        if self.actor is None:
            return
        name = pick_animation(self.session.anim_input())
        if name not in self.anims:
            return
        a, w = self.actor, self.session.weapons
        if name != self.cur_anim:
            rate = 1.0
            if name in ("reload_pistol", "reload_rifle"):
                rate = a.getDuration(name) / max(0.1, w.wdef.reload_time)
            elif name == "melee_slash":
                rate = a.getDuration(name) / max(0.1, w.wdef.melee_time)
            if name in ONE_SHOT:
                a.play(name)
            else:
                a.loop(name)
            a.setPlayRate(rate, name)
            self.prev_anim, self.cur_anim, self.fade_t = self.cur_anim, name, 0.0
        if self.fade_t < 1.0:
            self.fade_t = min(1.0, self.fade_t + dt / FADE_TIME)
            a.setControlEffect(self.cur_anim, self.fade_t)
            if self.prev_anim and self.prev_anim != self.cur_anim:
                a.setControlEffect(self.prev_anim, 1.0 - self.fade_t)
                if self.fade_t >= 1.0:
                    a.stop(self.prev_anim)

    # ================================================================ selftest
    def run_selftest(self):
        s, F, results = self.session, FrameInput, []

        def run(n, **kw):
            for _ in range(n):
                self.step_frame(1 / 60, F(**kw))
                self.graphicsEngine.renderFrame()

        def check(name, ok):
            results.append((name, bool(ok)))
            print(("PASS " if ok else "FAIL ") + name)

        p = s.player
        run(30)
        check("idle on ground", p.body.on_ground)
        y0 = p.body.y
        run(60, move_y=1.0)
        walk = p.body.y - y0
        check("WASD forward moves player", walk > 1.0)
        y0 = p.body.y
        run(60, move_y=1.0, sprint=True)
        check("sprint faster than walk", p.body.y - y0 > walk)
        run(30)
        run(1, toggle_crouch=True)
        check("crouch", p.stance == "crouch")
        run(1, toggle_crouch=True)
        check("stand again", p.stance == "stand")
        run(1, jump=True)
        run(10)
        check("jump leaves ground", p.body.z > 0.05)
        run(90)
        run(1, toggle_sit=True)
        check("sit", p.stance == "sit")
        run(1, jump=True)
        a0 = s.weapons.slot.ammo
        run(1, fire=True)
        run(1)
        check("pistol fires", s.weapons.slot.ammo == a0 - 1)
        run(1, reload=True)
        run(150)
        check("pistol reload completes", s.weapons.slot.ammo == s.weapons.wdef.mag_size)
        run(1, switch_to=1)
        run(40)
        a0 = s.weapons.slot.ammo
        run(20, fire=True, aim=True)
        check("rifle fires full-auto", s.weapons.slot.ammo < a0 - 3)
        run(1, switch_to=2)
        run(40)
        before = len(self.log)
        run(1, fire=True)
        run(1)
        run(60)
        check("kukri melee event", any(e[0] == "melee" for e in self.log[before:]))
        if self.actor:
            check("all rig animations present", not (REQUIRED_ANIMS - self.anims))
        failed = [n for n, ok in results if not ok]
        print("SELFTEST", "OK" if not failed else "FAILED: " + ", ".join(failed))
        return not failed
