"""Tests for the pure-Python third-person logic (no Panda3D needed).
Run:  python -m unittest tests.test_tps_logic -v
"""
import math
import os
import random
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tps import config as C
from tps.anim_state import AnimInput, pick_animation
from tps.physics import Body, World, apply_spread
from tps.player import Input, PlayerController
from tps.weapons import DEFAULT_LOADOUT, MeleeSwing, Shot, WeaponSystem


def settle(body, world, t=1.0, dt=1 / 60):
    for _ in range(int(t / dt)):
        body.step(world, dt)


class PhysicsTests(unittest.TestCase):
    def test_falls_and_lands_on_ground(self):
        w, b = World(), Body(z=3.0)
        settle(b, w, 2.0)
        self.assertAlmostEqual(b.z, 0.0, places=3)
        self.assertTrue(b.on_ground)

    def test_wall_blocks_and_slides(self):
        w = World()
        w.add_box("wall", (-5, 2, 0), (5, 3, 3))
        b = Body(y=0.0)
        b.on_ground = True
        for _ in range(120):
            b.vy, b.vx = 3.0, 1.0
            b.step(w, 1 / 60)
        self.assertLess(b.y, 2.0 - b.radius + 1e-6)   # stopped by wall
        self.assertGreater(b.x, 0.5)                  # still slid sideways

    def test_steps_onto_low_ledge_but_not_tall_box(self):
        w = World()
        w.add_box("ledge", (-1, 1, 0), (1, 3, 0.25))
        w.add_box("tall", (-1, 5, 0), (1, 7, 1.0))
        b = Body(y=0.0)
        for _ in range(240):
            b.vy = 2.0
            b.step(w, 1 / 60)
            if b.y > 4.0:
                break
        self.assertLess(b.y, 5.0 - b.radius + 1e-6)
        self.assertTrue(b.on_ground)

    def test_walking_up_ledge_raises_feet(self):
        w = World()
        w.add_box("ledge", (-1, 1, 0), (1, 3, 0.25))
        b = Body(y=0.0)
        for _ in range(60):          # ends at y ~ 2, still on the ledge (y 1..3)
            b.vy = 2.0
            b.step(w, 1 / 60)
        self.assertAlmostEqual(b.z, 0.25, places=3)
        for _ in range(90):          # walks off the far side and drops back to ground
            b.vy = 2.0
            b.step(w, 1 / 60)
        self.assertAlmostEqual(b.z, 0.0, places=3)

    def test_jump_height_and_landing(self):
        w, b = World(), Body()
        settle(b, w, 0.2)
        b.jump()
        peak = 0.0
        for _ in range(120):
            b.step(w, 1 / 60)
            peak = max(peak, b.z)
        expected = C.JUMP_SPEED ** 2 / (2 * C.GRAVITY)
        self.assertAlmostEqual(peak, expected, delta=0.05)
        self.assertTrue(b.on_ground)

    def test_cannot_jump_in_air(self):
        w, b = World(), Body(z=2.0)
        b.step(w, 1 / 60)
        b.jump()
        self.assertLess(b.vz, 0)

    def test_head_bump_under_ceiling(self):
        w = World()
        w.add_box("beam", (-2, -2, 2.0), (2, 2, 2.5))
        b = Body()
        settle(b, w, 0.2)
        b.jump()
        for _ in range(60):
            b.step(w, 1 / 60)
        self.assertLessEqual(b.z + b.height, 2.0 + 1e-6)

    def test_can_stand_check(self):
        w = World()
        w.add_box("low", (-2, -2, 1.3), (2, 2, 1.6))
        self.assertFalse(w.can_stand(0, 0, 0, C.BODY_RADIUS, C.STAND_HEIGHT))
        self.assertTrue(w.can_stand(0, 0, 0, C.BODY_RADIUS, C.CROUCH_HEIGHT))

    def test_raycast_hits_box_ground_and_misses(self):
        w = World()
        box = w.add_box("t", (-1, 10, 0), (1, 11, 2), hp=50)
        hit = w.raycast((0, 0, 1), (0, 1, 0), 50)
        self.assertIs(hit.box, box)
        self.assertAlmostEqual(hit.dist, 10.0, places=5)
        g = w.raycast((0, 0, 2), (0, 1, -1), 50)
        self.assertIsNone(g.box if g and g.point[1] < 10 else None)
        self.assertIsNone(w.raycast((0, 0, 1), (0, -1, 0), 50))
        self.assertIsNone(w.raycast((0, 0, 1), (0, 1, 0), 5))

    def test_spread_within_cone(self):
        rng = random.Random(1)
        for _ in range(200):
            d = apply_spread((0, 1, 0), 3.0, rng)
            ang = math.degrees(math.acos(max(-1, min(1, d[1]))))
            self.assertLessEqual(ang, 3.0 + 1e-6)
        self.assertEqual(apply_spread((0, 1, 0), 0, rng), (0, 1, 0))


class WeaponTests(unittest.TestCase):
    def setUp(self):
        self.ws = WeaponSystem(DEFAULT_LOADOUT, random.Random(0))
        self.ws.switch_left = 0.0

    def fire_frames(self, ws, n, held=True, dt=1 / 60):
        shots = []
        for _ in range(n):
            s, _ = ws.pull_trigger(held)
            shots += s
            ws.update(dt)
        return shots

    def test_pistol_semi_auto_one_shot_per_press(self):
        ws = self.ws
        shots = self.fire_frames(ws, 60, held=True)
        self.assertEqual(len(shots), 1)
        self.assertEqual(ws.slot.ammo, 7)

    def test_pistol_fire_rate(self):
        ws = self.ws
        count = 0
        for _ in range(120):                       # 2 s alternating release/press
            for held in (True, False):
                s, _ = ws.pull_trigger(held)
                count += len(s)
                ws.update(1 / 120)
        self.assertEqual(count, 8)   # 300 rpm allows 10 in 2 s, but the magazine holds 8

    def test_rifle_full_auto_rate(self):
        ws = self.ws
        ws.switch_to(1)
        ws.update(1.0)
        shots = self.fire_frames(ws, 60)
        self.assertTrue(9 <= len(shots) <= 12, len(shots))     # 650 rpm ~ 10.8/s
        self.assertEqual(ws.slot.ammo, 30 - len(shots))

    def test_recoil_builds_and_recovers(self):
        ws = self.ws
        ws.switch_to(1)
        ws.update(1.0)
        self.fire_frames(ws, 20)
        self.assertGreater(ws.recoil_pitch, 0.02)
        for _ in range(180):
            ws.update(1 / 60)
        self.assertLess(ws.recoil_pitch, 0.002)

    def test_reload_math_and_timing(self):
        ws = self.ws
        ws.slot.ammo, ws.slot.reserve = 2, 5
        self.assertEqual(ws.start_reload(), [("reload_start", 0)])
        ws.update(1.0)
        self.assertEqual(ws.slot.ammo, 2)          # not done yet
        _, ev = ws.update(1.0)
        self.assertIn(("reload_end", 0), ev)
        self.assertEqual((ws.slot.ammo, ws.slot.reserve), (7, 0))

    def test_no_reload_when_full_or_no_reserve(self):
        ws = self.ws
        self.assertEqual(ws.start_reload(), [])
        ws.slot.ammo, ws.slot.reserve = 3, 0
        self.assertEqual(ws.start_reload(), [])

    def test_cannot_fire_while_reloading_and_dry_autoreloads(self):
        ws = self.ws
        ws.slot.ammo = 0
        s, ev = ws.pull_trigger(True)
        self.assertEqual(s, [])
        self.assertIn(("dry", 0), ev)
        self.assertTrue(ws.reloading)
        ws.pull_trigger(False)
        s, _ = ws.pull_trigger(True)
        self.assertEqual(s, [])

    def test_switch_cancels_reload_and_blocks_fire(self):
        ws = self.ws
        ws.slot.ammo = 1
        ws.start_reload()
        ev = ws.switch_to(1)
        self.assertEqual(ev, [("switch", 1)])
        self.assertFalse(ws.reloading)
        s, _ = ws.pull_trigger(True)
        self.assertEqual(s, [])                    # switch lock
        ws.update(0.6)
        ws.pull_trigger(False)
        s, _ = ws.pull_trigger(True)
        self.assertEqual(len(s), 1)

    def test_aiming_reduces_spread(self):
        ws = self.ws
        hip, _ = ws.pull_trigger(True, aiming=False)
        ws2 = WeaponSystem(DEFAULT_LOADOUT, random.Random(0))
        ws2.switch_left = 0.0
        aim, _ = ws2.pull_trigger(True, aiming=True)
        self.assertLess(aim[0].spread_deg, hip[0].spread_deg)

    def test_melee_swing_lands_once_at_hit_time(self):
        ws = self.ws
        ws.switch_to(2)
        ws.update(1.0)
        _, ev = ws.pull_trigger(True)
        self.assertEqual(ev, [("melee", 2)])
        hits = []
        for _ in range(60):
            out, _ = ws.update(1 / 60)
            hits += out
        self.assertEqual(len(hits), 1)
        self.assertIsInstance(hits[0], MeleeSwing)
        self.assertEqual(ws.melee_left, 0.0)

    def test_melee_needs_fresh_press(self):
        ws = self.ws
        ws.switch_to(2)
        ws.update(1.0)
        ws.pull_trigger(True)
        for _ in range(60):
            ws.update(1 / 60)
        _, ev = ws.pull_trigger(True)              # still held, no new press
        self.assertEqual(ev, [])


class PlayerTests(unittest.TestCase):
    def run_input(self, pc, inp, t, dt=1 / 60):
        for _ in range(int(t / dt)):
            pc.update(dt, inp)

    def test_forward_moves_along_camera_direction(self):
        pc = PlayerController(World())
        self.run_input(pc, Input(move_y=1.0), 1.0)
        self.assertGreater(pc.body.y, 1.5)
        self.assertAlmostEqual(pc.body.x, 0.0, places=2)

    def test_camera_yaw_rotates_movement(self):
        pc = PlayerController(World())
        pc.cam_yaw = math.pi / 2                      # camera turned left
        self.run_input(pc, Input(move_y=1.0), 1.0)
        self.assertLess(pc.body.x, -1.5)

    def test_strafe_right(self):
        pc = PlayerController(World())
        self.run_input(pc, Input(move_x=1.0), 1.0)
        self.assertGreater(pc.body.x, 1.5)

    def test_sprint_faster_than_walk_and_crouch_slowest(self):
        def dist(inp, crouch=False):
            pc = PlayerController(World())
            if crouch:
                pc.update(1 / 60, Input(toggle_crouch=True))
            self.run_input(pc, inp, 2.0)
            return pc.body.y
        walk, sprint = dist(Input(move_y=1)), dist(Input(move_y=1, sprint=True))
        crouch = dist(Input(move_y=1), crouch=True)
        aim = dist(Input(move_y=1, aim=True))
        self.assertGreater(sprint, walk)
        self.assertGreater(walk, aim)
        self.assertGreater(aim, crouch)

    def test_crouch_toggle_changes_height_and_blocked_by_ceiling(self):
        w = World()
        w.add_box("low", (-3, -3, 1.3), (3, 3, 1.6))
        pc = PlayerController(w)
        pc.update(1 / 60, Input(toggle_crouch=True))
        self.assertEqual(pc.stance, "crouch")
        self.assertEqual(pc.body.height, C.CROUCH_HEIGHT)
        pc.update(1 / 60, Input(toggle_crouch=True))
        self.assertEqual(pc.stance, "crouch")        # no room to stand
        w.boxes.clear()
        pc.update(1 / 60, Input(toggle_crouch=True))
        self.assertEqual(pc.stance, "stand")

    def test_sit_only_when_still_and_blocks_movement(self):
        pc = PlayerController(World())
        self.run_input(pc, Input(), 0.3)
        pc.update(1 / 60, Input(toggle_sit=True))
        self.assertEqual(pc.stance, "sit")
        y0 = pc.body.y
        self.run_input(pc, Input(move_y=1.0), 1.0)
        self.assertAlmostEqual(pc.body.y, y0, places=2)
        pc.update(1 / 60, Input(jump=True))
        self.assertEqual(pc.stance, "stand")

    def test_cannot_sit_while_moving(self):
        pc = PlayerController(World())
        self.run_input(pc, Input(move_y=1.0), 0.5)
        pc.update(1 / 60, Input(move_y=1.0, toggle_sit=True))
        self.assertEqual(pc.stance, "stand")

    def test_jump_leaves_ground(self):
        pc = PlayerController(World())
        self.run_input(pc, Input(), 0.3)
        pc.update(1 / 60, Input(jump=True))
        self.run_input(pc, Input(), 0.2)
        self.assertGreater(pc.body.z, 0.1)
        self.run_input(pc, Input(), 1.5)
        self.assertTrue(pc.body.on_ground)

    def test_pitch_clamped_and_mouse_direction(self):
        pc = PlayerController(World())
        pc.update(1 / 60, Input(look_dx=100))
        self.assertLess(pc.cam_yaw, 0)               # mouse right => turn right (yaw decreases)
        for _ in range(100):
            pc.update(1 / 60, Input(look_dy=-500))
        self.assertAlmostEqual(pc.cam_pitch, C.PITCH_MAX, places=6)
        for _ in range(100):
            pc.update(1 / 60, Input(look_dy=500))
        self.assertAlmostEqual(pc.cam_pitch, C.PITCH_MIN, places=6)

    def test_aim_faces_camera_and_moving_faces_velocity(self):
        pc = PlayerController(World())
        pc.cam_yaw = 0.8
        self.run_input(pc, Input(aim=True), 1.0)
        self.assertAlmostEqual(pc.face_yaw, 0.8, places=2)
        pc2 = PlayerController(World())
        self.run_input(pc2, Input(move_x=1.0), 1.0)
        self.assertAlmostEqual(pc2.face_yaw, -math.pi / 2, places=1)

    def test_camera_behind_player_and_pulled_in_by_wall(self):
        w = World()
        pc = PlayerController(w)
        pos, h, p = pc.camera_transform()
        self.assertLess(pos[1], pc.body.y)           # behind (yaw 0 faces +Y)
        free = math.dist(pos[:2], (pc.body.x, pc.body.y))
        w.add_box("wall", (-5, -1.6, 0), (5, -1.5, 4))
        pos2, _, _ = pc.camera_transform()
        self.assertLess(math.dist(pos2[:2], (pc.body.x, pc.body.y)), free)
        self.assertGreater(pos2[1], -1.5)            # stays in front of the wall

    def test_aim_ray_hits_target_in_front(self):
        w = World()
        t = w.add_box("target", (-1.2, 12, 0), (1.2, 12.3, 2.2), hp=100)   # camera sits ~0.55 m right of the player
        pc = PlayerController(w, z=0)
        pc.cam_pitch = 0.0
        origin, d = pc.aim_ray()
        hit = w.raycast(origin, d, 100)
        self.assertIsNotNone(hit)
        self.assertIs(hit.box, t)


class AnimTests(unittest.TestCase):
    def test_priority_and_selection(self):
        A = AnimInput
        self.assertEqual(pick_animation(A()), "idle")
        self.assertEqual(pick_animation(A(moving=True)), "walk")
        self.assertEqual(pick_animation(A(moving=True, sprinting=True)), "sprint")
        self.assertEqual(pick_animation(A(stance="crouch")), "crouch_idle")
        self.assertEqual(pick_animation(A(stance="crouch", moving=True)), "crouch_walk")
        self.assertEqual(pick_animation(A(stance="sit")), "sit")
        self.assertEqual(pick_animation(A(airborne=True)), "jump")
        self.assertEqual(pick_animation(A(aiming=True, aim_anim="aim_rifle")), "aim_rifle")
        self.assertEqual(pick_animation(A(aiming=True, weapon_kind="melee")), "idle")
        self.assertEqual(pick_animation(A(reloading=True, reload_anim="reload_rifle", airborne=True)), "reload_rifle")
        self.assertEqual(pick_animation(A(meleeing=True, reloading=True, reload_anim="x")), "melee_slash")


if __name__ == "__main__":
    unittest.main()


class SessionTests(unittest.TestCase):
    def make(self):
        from tps.session import FrameInput, GameSession
        s = GameSession(seed=3)
        return s, FrameInput

    def face_target(self, s, name, shoulder=C.CAM_SHOULDER_AIM):
        """Stand 10 m back with the crosshair (camera ray) on the target. The over-the-
        shoulder camera sits `shoulder` m to the right of the body, so shift left."""
        t = next(b for b in s.world.boxes if b.name == name)
        cx, cy = (t.lo[0] + t.hi[0]) / 2, (t.lo[1] + t.hi[1]) / 2
        s.player.body.x, s.player.body.y = cx - shoulder, cy - 10
        s.player.cam_yaw = 0.0
        s.player.cam_pitch = 0.0
        s.player.face_yaw = 0.0
        return t

    def test_pistol_shots_destroy_target_and_it_respawns(self):
        s, F = self.make()
        t = self.face_target(s, "target_2")
        events = []
        for i in range(400):
            events += s.update(1 / 60, F(fire=(i % 20 < 2), aim=True))
            if t.dead:
                break
        self.assertTrue(t.dead)
        self.assertIn(("destroyed", "target_2"), events)
        self.assertEqual(s.kills, 1)
        hits = [e for e in events if e[0] == "hit"]
        self.assertTrue(all(h[1] == "target_2" for h in hits))
        for _ in range(int(5 / (1 / 60))):
            s.update(1 / 60, F())
        self.assertFalse(t.dead)
        self.assertEqual(t.hp, t.max_hp)

    def test_dead_target_does_not_block_rays(self):
        s, F = self.make()
        t = self.face_target(s, "target_2")
        t.dead, t.solid = True, False
        hit = s.world.raycast((t.lo[0] + 0.4, t.lo[1] - 5, 1.0), (0, 1, 0), 50)
        self.assertNotEqual(getattr(hit.box, "name", None), "target_2")

    def test_rifle_burst_consumes_ammo_and_reloads(self):
        s, F = self.make()
        self.face_target(s, "target_far_0")
        s.update(1 / 60, F(switch_to=1))
        for _ in range(40):
            s.update(1 / 60, F())
        for _ in range(30):
            s.update(1 / 60, F(fire=True, aim=True))
        ammo = s.weapons.slot.ammo
        self.assertLess(ammo, 30)
        ev = s.update(1 / 60, F(reload=True))
        self.assertIn(("reload_start", 1), ev)
        for _ in range(200):
            s.update(1 / 60, F())
        self.assertEqual(s.weapons.slot.ammo, 30)

    def test_melee_kills_target_in_front(self):
        s, F = self.make()
        t = self.face_target(s, "target_1", shoulder=0.0)
        s.player.body.y = t.lo[1] - 1.2
        s.update(1 / 60, F(switch_to=2))
        for _ in range(40):
            s.update(1 / 60, F())
        events = []
        for i in range(120):
            events += s.update(1 / 60, F(fire=(i == 0)))
        self.assertIn(("melee", 2), events)
        self.assertEqual([e for e in events if e[0] == "hit"][0][2], 65)
        self.assertEqual(t.hp, 35)

    def test_events_for_jump_and_land(self):
        s, F = self.make()
        for _ in range(20):
            s.update(1 / 60, F())
        ev = s.update(1 / 60, F(jump=True))
        self.assertIn(("jump",), ev)
        landed = False
        for _ in range(120):
            landed |= ("land",) in s.update(1 / 60, F())
        self.assertTrue(landed)

    def test_anim_input_follows_state(self):
        from tps.anim_state import pick_animation
        s, F = self.make()
        for _ in range(20):
            s.update(1 / 60, F())
        self.assertEqual(pick_animation(s.anim_input()), "idle")
        for _ in range(60):
            s.update(1 / 60, F(move_y=1.0, sprint=True))
        self.assertEqual(pick_animation(s.anim_input()), "sprint")
        s.weapons.slot.ammo = 1
        s.update(1 / 60, F(reload=True))
        self.assertEqual(pick_animation(s.anim_input()), "reload_pistol")

    def test_testbed_geometry_crouch_under_beam_and_step_up(self):
        s, F = self.make()
        p = s.player
        p.body.x, p.body.y = -8.0, -2.0
        p.update(1 / 60, Input(toggle_crouch=True))
        for _ in range(400):
            p.update(1 / 60, Input(move_y=1.0))
        self.assertGreater(p.body.y, 4.0)                    # passed under the beam (y 2..3)
        self.assertEqual(p.stance, "crouch")
        p.body.x, p.body.y, p.body.z = 7.5, 0.0, 0.0
        for _ in range(90):
            p.update(1 / 60, Input(move_y=1.0))
        self.assertAlmostEqual(p.body.z, 0.25, places=2)     # walked onto the low step


class SfxTests(unittest.TestCase):
    def test_generates_valid_wavs(self):
        import tempfile
        import wave
        from tps.sfx import generate_all
        with tempfile.TemporaryDirectory() as d:
            names = generate_all(d)
            self.assertGreaterEqual(len(names), 10)
            for n in names:
                with wave.open(os.path.join(d, n)) as w:
                    self.assertEqual(w.getframerate(), 44100)
                    self.assertGreater(w.getnframes(), 1000)
