import sys
import os
import math
import logging

if sys.platform == 'win32':
    try:
        import ctypes
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass

import pygame
logger = logging.getLogger("Sector9")
from src.config import (
    SCREEN_WIDTH, SCREEN_HEIGHT, RENDER_WIDTH, RENDER_HEIGHT, FPS,
    FOV, HALF_FOV,
    COLOR_CYAN, COLOR_CYAN_GLOW, COLOR_ALERT_RED, COLOR_AMBER, COLOR_GREEN, COLOR_WHITE,
    IMAGES_DIR
)
from src.sound_system import SoundSystem
from src.player import Player
from src.raycaster import Raycaster
from src.sprite_renderer import SpriteRenderer
from src.dialogue_system import DialogueManager
from src.quest_system import QuestManager
from src.ui_manager import UIManager
from src.cinematics import CinematicsManager
from src.save_system import SaveSystem
from src.levels import LevelManager
from src.ai_watcher import WatcherDrone
from src.puzzles import (
    BridgeDoorOverridePuzzle, PowerRoutingPuzzle, MedicalKeypadPuzzle,
    BiohazardValvesPuzzle, DefenseMatrixPuzzle, TransceiverAlignmentPuzzle,
    SeraHarmonicPuzzle, PrimeDirectivePuzzle
)

class GameEngine:
    def __init__(self, headless=False):
        pygame.init()
        self.headless = headless
        self.is_fullscreen = True

        if headless:
            os.environ['SDL_VIDEODRIVER'] = 'dummy'
            self.screen_width = 320
            self.screen_height = 240
            self.screen = pygame.display.set_mode((self.screen_width, self.screen_height))
        else:
            # Fullscreen by default with monitor detection
            info = pygame.display.Info()
            w = info.current_w if info.current_w > 0 else SCREEN_WIDTH
            h = info.current_h if info.current_h > 0 else SCREEN_HEIGHT
            self.screen_width = max(1024, w)
            self.screen_height = max(768, h)
            try:
                self.screen = pygame.display.set_mode(
                    (self.screen_width, self.screen_height),
                    pygame.FULLSCREEN | pygame.DOUBLEBUF | pygame.HWSURFACE
                )
            except Exception as e:
                print(f"[GameEngine] Fullscreen fallback: {e}")
                try:
                    self.screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN | pygame.DOUBLEBUF)
                except Exception:
                    self.is_fullscreen = False
                    self.screen_width = SCREEN_WIDTH
                    self.screen_height = SCREEN_HEIGHT
                    self.screen = pygame.display.set_mode((self.screen_width, self.screen_height), pygame.DOUBLEBUF)

            self.screen_width, self.screen_height = self.screen.get_size()
            pygame.display.set_caption("SECTOR 9: THE LAST DIRECTIVE")

        self.clock = pygame.time.Clock()
        self.render_surf = pygame.Surface((RENDER_WIDTH, RENDER_HEIGHT))

        self.sound = SoundSystem.get_instance()
        self.raycaster = Raycaster(RENDER_WIDTH, RENDER_HEIGHT)
        self.sprite_renderer = SpriteRenderer()
        self.dialogue = DialogueManager()
        self.quest_mgr = QuestManager()
        self.ui_mgr = UIManager()
        self.cinematics = CinematicsManager()

        self.player = Player()
        self.state = 'MAIN_MENU'
        self.mouse_captured = False
        self.game_timer = 0.0

        self.current_level = None
        self.level_map = []
        self.sprites = []
        self.watcher_drones = []
        self.active_puzzle = None
        self.interaction_prompt = ""
        self.feedback_message = ""
        self.feedback_timer = 0.0

        # Ending state
        self.selected_ending = "A"
        self.ending_stage = 0
        self.ending_timer = 0.0

        # Menu options
        self.menu_options = ["NEW CAMPAIGN", "CONTINUE MISSION", "MISSION DOSSIER (BACKSTORY)", "CONTROLS", "CREDITS", "EXIT"]
        self.menu_idx = 0
        self.menu_btn_rects = []
        self.credits_active = False
        self.controls_active = False
        self.briefing_voice_idx = 0
        self.briefing_voice_timer = 0.0
        self.briefing_clips = ['briefing_intro', 'briefing_star', 'briefing_directive']

        self.load_chapter_level(0)

    def toggle_fullscreen(self):
        if self.headless: return
        self.is_fullscreen = not self.is_fullscreen
        if self.is_fullscreen:
            info = pygame.display.Info()
            w = info.current_w if info.current_w > 0 else SCREEN_WIDTH
            h = info.current_h if info.current_h > 0 else SCREEN_HEIGHT
            self.screen_width = max(1024, w)
            self.screen_height = max(768, h)
            try:
                self.screen = pygame.display.set_mode(
                    (self.screen_width, self.screen_height),
                    pygame.FULLSCREEN | pygame.DOUBLEBUF | pygame.HWSURFACE
                )
            except Exception:
                try:
                    self.screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN | pygame.DOUBLEBUF)
                except Exception:
                    self.is_fullscreen = False
                    self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.DOUBLEBUF)
        else:
            self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.DOUBLEBUF)
        self.screen_width, self.screen_height = self.screen.get_size()

    def toggle_mouse(self, capture):
        if self.headless: return
        self.mouse_captured = capture
        try:
            pygame.event.set_grab(capture)
        except Exception:
            pass
        try:
            pygame.mouse.set_visible(not capture)
        except Exception:
            pass

    def load_chapter_level(self, chapter_id):
        self.quest_mgr.current_chapter = chapter_id
        level_data = LevelManager.get_level(chapter_id)
        self.current_level = level_data
        self.level_map = [list(r) for r in level_data.map_grid]
        self.sprites = list(level_data.sprites)

        sp_x, sp_y, sp_a = level_data.player_spawn
        self.player.x = sp_x
        self.player.y = sp_y
        self.player.angle = sp_a
        self.player.set_checkpoint(sp_x, sp_y, sp_a)

        self.watcher_drones = []
        if chapter_id == 2:
            drone = WatcherDrone(9.5, 5.5, patrol_route=[(9.5, 5.5), (9.5, 6.5), (12.5, 6.5), (12.5, 5.5)], drone_id="drone_ch2")
            self.watcher_drones.append(drone)
        elif chapter_id == 4:
            drone = WatcherDrone(8.5, 2.5, patrol_route=[(8.5, 2.5), (14.5, 2.5), (14.5, 6.5), (8.5, 6.5)], drone_id="drone_ch4")
            self.watcher_drones.append(drone)

        if chapter_id > 0:
            SaveSystem.save_game("autosave", self.player, self.quest_mgr, self.level_map)

    def start_new_game(self):
        logger.info("start_new_game called")
        self.state = 'MISSION_BRIEFING'
        self.toggle_mouse(False)
        self.briefing_voice_idx = 0
        self.briefing_voice_timer = 0.0
        self.sound.start_ambient('ambient_dreadnought_hum')
        self.sound.play_voice_clip(self.briefing_clips[0])
        logger.info("Entered MISSION_BRIEFING with full backstory transmission")

    def open_backstory_briefing(self):
        self.state = 'MISSION_BRIEFING'
        self.toggle_mouse(False)
        self.briefing_voice_idx = 0
        self.briefing_voice_timer = 0.0
        self.sound.start_ambient('ambient_dreadnought_hum')
        self.sound.play_voice_clip(self.briefing_clips[0])

    def deploy_from_briefing(self):
        logger.info("deploy_from_briefing called")
        self.sound.play('access_granted')
        self.sound.play('door_open')
        self.player = Player()
        self.quest_mgr = QuestManager()
        self.load_chapter_level(0)
        self.state = 'PLAYING'
        self.toggle_mouse(True)
        self.cinematics.run_prologue_cutscene(self.screen, self.clock, self.dialogue, self._on_prologue_done)
        logger.info(f"deploy_from_briefing complete, state={self.state}")

    def _on_prologue_done(self):
        logger.info("_on_prologue_done called, continuing PLAYING")
        self.state = 'PLAYING'
        self.toggle_mouse(True)
        self.feedback_message = "DIRECTIVE: Search fallen officer in East Bridge Bay for Access Card"
        self.feedback_timer = 6.0
        logger.info("_on_prologue_done complete")

    def launch_puzzle(self, puzzle_instance):
        self.active_puzzle = puzzle_instance
        self.state = 'PUZZLE'
        self.toggle_mouse(False)

    def get_current_objective_target(self):
        """Finds coordinates of current prime objective for the HUD compass."""
        ch = self.quest_mgr.current_chapter
        if ch == 0:
            if not self.player.has_item("Emergency Access Card"):
                return (9.5, 2.0, "FALLEN OFFICER (ACCESS CARD)")
            elif not self.quest_mgr.has_flag("bridge_unlocked"):
                return (3.5, 4.0, "BULKHEAD DOOR (OVERRIDE / SCAN)")
            else:
                return (7.5, 6.5, "ENGINEERING LIFT")
        elif ch == 1:
            if not self.player.has_item("Maintenance Tool"):
                return (11.5, 5.5, "MAINTENANCE TOOL CABINET")
            elif not self.quest_mgr.has_flag("power_restored"):
                return (10.5, 2.5, "POWER ROUTING TERMINAL")
            else:
                return (11.5, 7.5, "SECTOR LIFT (DECK 02)")
        elif ch == 2:
            if not self.player.has_item("Science Director's Badge"):
                return (11.5, 2.5, "MEDICAL EMERGENCY LOCKER")
            else:
                return (14.5, 6.5, "CENTRAL SECURITY BULKHEAD")
        elif ch == 3:
            if not self.player.has_item("Hazard-Filter Upgrade"):
                return (2.5, 2.5, "FILTER FABRICATION BENCH")
            elif not self.quest_mgr.has_flag("containment_stable"):
                return (11.5, 2.5, "BIOHAZARD VALVES PANEL")
            else:
                return (14.5, 6.5, "CORE VAULT LIFT")
        elif ch == 4:
            if not self.quest_mgr.has_flag("matrix_disabled"):
                return (13.5, 2.5, "DEFENSE MATRIX CONSOLE")
            else:
                return (16.5, 6.5, "COMMS DECK LIFT")
        elif ch == 5:
            if not self.quest_mgr.has_flag("distress_sent"):
                return (14.5, 2.5, "TRANSCEIVER ALIGNMENT ARRAY")
            else:
                return (18.5, 6.5, "CONTINUUM ENGINE LIFT")
        elif ch == 6:
            return (15.5, 7.5, "PRIME DIRECTIVE TERMINAL")
        return None

    def handle_interactions(self):
        px, py = int(self.player.x), int(self.player.y)
        self.interaction_prompt = ""

        fx = int(self.player.x + math.cos(self.player.angle) * 0.95)
        fy = int(self.player.y + math.sin(self.player.angle) * 0.95)

        target_coords = [(fx, fy), (px, py)]
        for dx in [-1, 0, 1]:
            for dy in [-1, 0, 1]:
                target_coords.append((px + dx, py + dy))

        found_action = None
        for cx, cy in target_coords:
            if (cx, cy) in self.current_level.interactions:
                info = self.current_level.interactions[(cx, cy)]
                found_action = (cx, cy, info)
                break

        if not found_action:
            for sp in self.sprites:
                if sp.interactive and sp.active:
                    dist = math.hypot(sp.x - self.player.x, sp.y - self.player.y)
                    if dist <= 1.5:
                        self.interaction_prompt = sp.label
                        return ("sprite", sp)

        if found_action:
            cx, cy, info = found_action
            t = info.get("type")
            if t == "door_puzzle":
                self.interaction_prompt = "[E] Access Bulkhead Security Panel (Card / Password)"
            elif t == "door":
                req = info.get("requires")
                req_flag = info.get("requires_flag")
                if req and not self.player.has_item(req):
                    self.interaction_prompt = f"[E] Locked Door (Requires: {req})"
                elif req_flag and not self.quest_mgr.has_flag(req_flag):
                    self.interaction_prompt = "[E] Locked Door (Security Lock Active)"
                else:
                    self.interaction_prompt = "[E] Open Bulkhead Door"
            elif t == "puzzle":
                self.interaction_prompt = "[E] Access Security Terminal"
            elif t == "lift":
                if self.quest_mgr.is_chapter_complete():
                    self.interaction_prompt = "[E] Enter Sector Lift"
                else:
                    self.interaction_prompt = "[E] Lift Offline (Complete Directives First)"
            elif t == "item":
                self.interaction_prompt = f"[E] Collect {info.get('item', 'Item')}"
            elif t == "lore":
                self.interaction_prompt = "[E] Read Archive Data"
            elif t == "distraction":
                self.interaction_prompt = "[E] Trigger Alarm Distraction"
            elif t == "dialogue":
                self.interaction_prompt = "[E] Speak with The Watcher"
            elif t == "console":
                self.interaction_prompt = "[E] Inspect Console"

            return ("coord", cx, cy, info)

        return None

    def execute_interaction(self, target):
        if not target: return
        t_type = target[0]

        if t_type == "sprite":
            sp = target[1]
            if sp.entity_id == "fallen_officer":
                if self.player.add_item("Emergency Access Card"):
                    self.quest_mgr.complete_objective("get_access_card", self.player)
                    self.feedback_message = "Retrieved Emergency Access Card."
                    self.feedback_timer = 4.0
            elif sp.entity_id == "hale_chip_sprite":
                self.player.add_log("hale_chip", "Technician Hale's Data Chip")
                self.quest_mgr.complete_objective("inspect_console", self.player)
                self.quest_mgr.complete_objective("read_hale_chip", self.player)
                self.feedback_message = "Read Technician Hale's Data Chip."
                self.feedback_timer = 4.0
            elif sp.entity_id == "tool_sprite":
                if self.player.add_item("Maintenance Tool"):
                    self.quest_mgr.complete_objective("find_tool", self.player)
                    self.feedback_message = "Retrieved Maintenance Tool."
                    self.feedback_timer = 4.0
                    sp.active = False
            elif sp.entity_id == "malik_log_sprite":
                self.player.add_log("malik_personal_log", "Malik's Personal Recording")
                self.quest_mgr.complete_objective("malik_promise", self.player)
                self.feedback_message = "Discovered Malik's Personal Log."
                self.feedback_timer = 4.0
            elif sp.entity_id == "med_records_sprite":
                self.player.add_log("ch2_patient_records", "Patient Admission Records")
                self.quest_mgr.complete_objective("inspect_medical", self.player)
                self.feedback_message = "Examined Medical Records."
                self.feedback_timer = 4.0
            elif sp.entity_id == "filter_station_sprite":
                if self.player.add_item("Hazard-Filter Upgrade"):
                    self.quest_mgr.complete_objective("find_filter_parts", self.player)
                    self.quest_mgr.complete_objective("fabricate_filter", self.player)
                    self.feedback_message = "Fabricated Hazard-Filter Upgrade."
                    self.feedback_timer = 4.0
                    sp.active = False
            elif sp.entity_id in ["c1_sprite", "c2_sprite", "c3_sprite"]:
                frag_name = "Master Cipher Fragment"
                self.player.add_item(frag_name)
                self.feedback_message = f"Recovered {frag_name}."
                self.feedback_timer = 4.0
                sp.active = False
                if self.player.inventory.count(frag_name) >= 3:
                    self.quest_mgr.complete_objective("find_cipher_frags", self.player)
            elif sp.entity_id == "sera_holo_sprite":
                self.launch_puzzle(SeraHarmonicPuzzle())
            elif sp.entity_id == "watcher_boss_sprite":
                self.dialogue.start_dialogue_by_id("chapter_6", "final_conversation", lambda: self.quest_mgr.complete_objective("confront_watcher_core", self.player))
            elif sp.entity_id in ["proj_1_sprite", "proj_2_sprite", "proj_3_sprite"]:
                self.quest_mgr.complete_objective("examine_projections", self.player)
                self.feedback_message = "Examined Quantum Memory Projection."
                self.feedback_timer = 4.0

        elif t_type == "coord":
            _, cx, cy, info = target
            action_type = info.get("type")

            if action_type == "door_puzzle":
                # Launches Bridge Door Override Keypad (supports card scan OR password 2847)
                has_card = self.player.has_item("Emergency Access Card")
                self.launch_puzzle(BridgeDoorOverridePuzzle(player_has_card=has_card))

            elif action_type == "door":
                req = info.get("requires")
                req_flag = info.get("requires_flag")
                can_open = True
                if req and not self.player.has_item(req): can_open = False
                if req_flag and not self.quest_mgr.has_flag(req_flag): can_open = False

                if can_open:
                    self.level_map[cy][cx] = 'O'
                    self.sound.play('access_granted')
                    self.feedback_message = "Bulkhead Door Unlocked."
                    self.feedback_timer = 4.0
                    if info.get("id") == "central_security_door":
                        self.quest_mgr.complete_objective("use_science_badge", self.player)
                        self.quest_mgr.complete_objective("evade_drone", self.player)
                else:
                    self.sound.play('access_denied')
                    self.feedback_message = "Security Credentials Required."
                    self.feedback_timer = 4.0

            elif action_type == "puzzle":
                pname = info.get("puzzle_name")
                if pname == "power_routing":
                    self.launch_puzzle(PowerRoutingPuzzle())
                elif pname == "medical_keypad":
                    self.launch_puzzle(MedicalKeypadPuzzle())
                elif pname == "biohazard_valves":
                    self.launch_puzzle(BiohazardValvesPuzzle())
                elif pname == "defense_matrix":
                    self.launch_puzzle(DefenseMatrixPuzzle())
                elif pname == "transceiver_align":
                    self.launch_puzzle(TransceiverAlignmentPuzzle())
                elif pname == "sera_harmonic":
                    self.launch_puzzle(SeraHarmonicPuzzle())
                elif pname == "prime_directive":
                    secret_ok = self.quest_mgr.can_access_secret_ending(self.player)
                    self.launch_puzzle(PrimeDirectivePuzzle(secret_unlocked=secret_ok))

            elif action_type == "lift":
                if self.quest_mgr.is_chapter_complete():
                    next_ch = info.get("next_chapter")
                    self.quest_mgr.advance_chapter(self.player)
                    self.load_chapter_level(next_ch)
                    self.state = 'CHAPTER_SPLASH'
                    self.toggle_mouse(False)
                    self.sound.play('access_granted')
                else:
                    self.sound.play('access_denied')
                    self.feedback_message = "Primary Directives Not Yet Complete."
                    self.feedback_timer = 4.0

            elif action_type == "distraction":
                for d in self.watcher_drones:
                    d.trigger_distraction(cx, cy, self.level_map)
                self.sound.play('spark')
                self.feedback_message = "Distraction alarm triggered! Sentry investigating."
                self.feedback_timer = 4.0

            elif action_type == "lore":
                lore_k = info.get("lore_key")
                lore_entry = self.ui_mgr.lore_data.get(lore_k, {})
                self.player.add_log(lore_k, lore_entry.get("title", lore_k))
                self.feedback_message = f"Logged: {lore_entry.get('title', lore_k)}"
                self.feedback_timer = 4.0

    def update(self, dt):
        self.game_timer += dt
        if self.feedback_timer > 0:
            self.feedback_timer -= dt

        if self.state == 'PLAYING':
            keys = pygame.key.get_pressed()
            mouse_dx = 0
            if self.mouse_captured and not self.headless:
                mouse_dx, _ = pygame.mouse.get_rel()

            self.player.handle_input(keys, mouse_dx, dt, self.level_map)
            self.handle_interactions()

            for drone in self.watcher_drones:
                alert_msg = drone.update(self.player, self.level_map, dt)
                if alert_msg:
                    self.feedback_message = alert_msg
                    self.feedback_timer = 3.0

            for sp in self.sprites:
                sp.update(dt)

            if self.dialogue.is_active:
                self.dialogue.update(dt)

        elif self.state == 'PUZZLE':
            self.active_puzzle.update(dt)
            if getattr(self.active_puzzle, 'exit_clicked', False):
                self.state = 'PLAYING'
                self.toggle_mouse(True)
                return

            if self.active_puzzle.is_completed:
                if isinstance(self.active_puzzle, BridgeDoorOverridePuzzle):
                    self.quest_mgr.set_flag("bridge_unlocked")
                    self.quest_mgr.complete_objective("unlock_bridge_door", self.player)
                    # Open door cell at (3, 4)
                    self.level_map[4][3] = 'O'
                    self.dialogue.start_dialogue_by_id("prologue", "door_open")
                elif isinstance(self.active_puzzle, PowerRoutingPuzzle):
                    self.quest_mgr.set_flag("power_restored")
                    self.quest_mgr.complete_objective("solve_power_grid", self.player)
                    self.quest_mgr.complete_objective("stabilize_regulator", self.player)
                    self.level_map[4][4] = 'O'
                    self.dialogue.start_dialogue_by_id("chapter_1", "ward_recording_1", lambda: self.quest_mgr.complete_objective("listen_ward_1", self.player))
                elif isinstance(self.active_puzzle, MedicalKeypadPuzzle):
                    self.quest_mgr.set_flag("medical_unlocked")
                    self.quest_mgr.complete_objective("unlock_locker", self.player)
                    self.player.add_item("Science Director's Badge")
                    self.level_map[4][4] = 'O'
                    self.dialogue.start_dialogue_by_id("chapter_2", "dr_sera_rec_1", lambda: self.quest_mgr.complete_objective("listen_sera_1", self.player))
                elif isinstance(self.active_puzzle, BiohazardValvesPuzzle):
                    self.quest_mgr.set_flag("containment_stable")
                    self.quest_mgr.complete_objective("solve_valves", self.player)
                    self.level_map[4][4] = 'O'
                    self.dialogue.start_dialogue_by_id("chapter_3", "revelation_stars", lambda: self.quest_mgr.complete_objective("listen_ward_sera_2", self.player))
                elif isinstance(self.active_puzzle, DefenseMatrixPuzzle):
                    self.quest_mgr.set_flag("matrix_disabled")
                    self.quest_mgr.complete_objective("reprogram_matrix", self.player)
                    self.level_map[4][4] = 'O'
                    self.dialogue.start_dialogue_by_id("chapter_4", "ward_secret", lambda: self.quest_mgr.complete_objective("listen_ward_secret", self.player))
                elif isinstance(self.active_puzzle, TransceiverAlignmentPuzzle):
                    self.quest_mgr.set_flag("distress_sent")
                    self.quest_mgr.complete_objective("align_dishes", self.player)
                    self.level_map[4][4] = 'O'
                    self.dialogue.start_dialogue_by_id("chapter_5", "future_call", lambda: self.quest_mgr.complete_objective("hear_future_aegis", self.player))
                elif isinstance(self.active_puzzle, SeraHarmonicPuzzle):
                    self.quest_mgr.set_flag("sera_synced")
                    self.quest_mgr.complete_objective("sera_hologram_quest", self.player)
                    self.dialogue.start_dialogue_by_id("chapter_5", "sera_hologram")
                elif isinstance(self.active_puzzle, PrimeDirectivePuzzle):
                    chosen = self.active_puzzle.result_code
                    self.quest_mgr.ending_selected = chosen
                    self.selected_ending = chosen
                    self.state = 'ENDING'
                    self.ending_stage = 0
                    self.toggle_mouse(False)
                    return

                self.state = 'PLAYING'
                self.toggle_mouse(True)

        elif self.state == 'MISSION_BRIEFING':
            if not self.sound.is_voice_playing():
                self.briefing_voice_timer += dt
                if self.briefing_voice_timer > 1.2:
                    self.briefing_voice_timer = 0.0
                    self.briefing_voice_idx += 1
                    if self.briefing_voice_idx < len(self.briefing_clips):
                        self.sound.play_voice_clip(self.briefing_clips[self.briefing_voice_idx])

        elif self.state == 'PROLOGUE_CUTSCENE':
            self.dialogue.update(dt)

        elif self.state == 'ENDING':
            self.ending_timer += dt

    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                logger.info("QUIT event received")
                pygame.quit()
                sys.exit()

            # Global Fullscreen Toggle
            if event.type == pygame.KEYDOWN and event.key == pygame.K_F11:
                self.toggle_fullscreen()
                continue

            if self.state == 'MAIN_MENU':
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    pos = event.pos
                    if self.credits_active or self.controls_active:
                        self.credits_active = False
                        self.controls_active = False
                        self.sound.play('ui_beep')
                    else:
                        for idx, btn_r in self.menu_btn_rects:
                            if btn_r.collidepoint(pos):
                                self.sound.play('ui_beep')
                                opt = self.menu_options[idx]
                                if opt == "NEW CAMPAIGN":
                                    self.start_new_game()
                                elif opt == "CONTINUE MISSION":
                                    if SaveSystem.load_game("autosave", self.player, self.quest_mgr):
                                        self.load_chapter_level(self.quest_mgr.current_chapter)
                                        self.state = 'PLAYING'
                                        self.toggle_mouse(True)
                                        self.sound.play('access_granted')
                                elif opt in ["MISSION DOSSIER (BACKSTORY)", "MISSION ARCHIVES"]:
                                    self.open_backstory_briefing()
                                elif opt == "CONTROLS":
                                    self.controls_active = True
                                elif opt == "CREDITS":
                                    self.credits_active = True
                                elif opt == "EXIT":
                                    pygame.quit()
                                    sys.exit()
                                break

                elif event.type == pygame.KEYDOWN:
                    if self.credits_active or self.controls_active:
                        self.credits_active = False
                        self.controls_active = False
                        self.sound.play('ui_beep')
                    elif event.key in [pygame.K_UP, pygame.K_w]:
                        self.menu_idx = (self.menu_idx - 1) % len(self.menu_options)
                        self.sound.play('ui_beep')
                    elif event.key in [pygame.K_DOWN, pygame.K_s]:
                        self.menu_idx = (self.menu_idx + 1) % len(self.menu_options)
                        self.sound.play('ui_beep')
                    elif event.key in [pygame.K_RETURN, pygame.K_SPACE]:
                        opt = self.menu_options[self.menu_idx]
                        if opt == "NEW CAMPAIGN":
                            self.start_new_game()
                        elif opt == "CONTINUE MISSION":
                            if SaveSystem.load_game("autosave", self.player, self.quest_mgr):
                                self.load_chapter_level(self.quest_mgr.current_chapter)
                                self.state = 'PLAYING'
                                self.toggle_mouse(True)
                                self.sound.play('access_granted')
                        elif opt in ["MISSION DOSSIER (BACKSTORY)", "MISSION ARCHIVES"]:
                            self.open_backstory_briefing()
                        elif opt == "CONTROLS":
                            self.controls_active = True
                            self.sound.play('ui_beep')
                        elif opt == "CREDITS":
                            self.credits_active = True
                            self.sound.play('ui_beep')
                        elif opt == "EXIT":
                            pygame.quit()
                            sys.exit()

            elif self.state == 'MISSION_BRIEFING':
                if event.type == pygame.KEYDOWN:
                    if event.key in [pygame.K_SPACE, pygame.K_RETURN]:
                        self.deploy_from_briefing()
                    elif event.key == pygame.K_m:
                        self.sound.play_voice_clip(self.briefing_clips[self.briefing_voice_idx % len(self.briefing_clips)])
                    elif event.key == pygame.K_ESCAPE:
                        self.state = 'MAIN_MENU'
                        self.sound.stop_ambient()
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    self.deploy_from_briefing()

            elif self.state == 'PLAYING':
                if self.dialogue.is_active:
                    self.dialogue.handle_input(event)
                    continue

                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_e:
                        target = self.handle_interactions()
                        self.execute_interaction(target)
                    elif event.key == pygame.K_f:
                        self.player.toggle_flashlight()
                    elif event.key in [pygame.K_TAB, pygame.K_j]:
                        self.state = 'JOURNAL'
                        self.toggle_mouse(False)
                        self.sound.play('ui_beep')
                    elif event.key == pygame.K_i:
                        self.state = 'INVENTORY'
                        self.toggle_mouse(False)
                        self.sound.play('ui_beep')
                    elif event.key == pygame.K_ESCAPE:
                        self.state = 'PAUSE'
                        self.toggle_mouse(False)
                        self.sound.play('ui_beep')

            elif self.state == 'PUZZLE':
                if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    self.state = 'PLAYING'
                    self.toggle_mouse(True)
                else:
                    self.active_puzzle.handle_input(event)

            elif self.state == 'JOURNAL':
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    pos = event.pos
                    # Close X
                    if self.ui_mgr.btn_close_journal_rect.collidepoint(pos):
                        self.state = 'PLAYING'
                        self.toggle_mouse(True)
                        self.sound.play('ui_beep')
                        continue

                    # Tabs
                    for t_idx, t_rect in enumerate(self.ui_mgr.journal_tab_rects):
                        if t_rect.collidepoint(pos):
                            self.ui_mgr.journal_tab = t_idx
                            self.sound.play('ui_beep')
                            break

                    # Logs selection
                    for l_idx, l_rect in self.ui_mgr.journal_log_rects:
                        if l_rect.collidepoint(pos):
                            self.ui_mgr.selected_log_idx = l_idx
                            self.sound.play('ui_beep')
                            break

                elif event.type == pygame.KEYDOWN:
                    if event.key in [pygame.K_ESCAPE, pygame.K_TAB, pygame.K_j]:
                        self.state = 'PLAYING'
                        self.toggle_mouse(True)
                    elif event.key in [pygame.K_1, pygame.K_KP1]:
                        self.ui_mgr.journal_tab = 0
                        self.sound.play('ui_beep')
                    elif event.key in [pygame.K_2, pygame.K_KP2]:
                        self.ui_mgr.journal_tab = 1
                        self.sound.play('ui_beep')
                    elif event.key in [pygame.K_3, pygame.K_KP3]:
                        self.ui_mgr.journal_tab = 2
                        self.sound.play('ui_beep')
                    elif event.key in [pygame.K_UP, pygame.K_w]:
                        self.ui_mgr.selected_log_idx = max(0, self.ui_mgr.selected_log_idx - 1)
                        self.sound.play('ui_beep')
                    elif event.key in [pygame.K_DOWN, pygame.K_s]:
                        self.ui_mgr.selected_log_idx = min(len(self.player.discovered_logs) - 1, self.ui_mgr.selected_log_idx + 1)
                        self.sound.play('ui_beep')

            elif self.state == 'INVENTORY':
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    if self.ui_mgr.btn_close_inv_rect.collidepoint(event.pos):
                        self.state = 'PLAYING'
                        self.toggle_mouse(True)
                        self.sound.play('ui_beep')
                elif event.type == pygame.KEYDOWN and event.key in [pygame.K_ESCAPE, pygame.K_i]:
                    self.state = 'PLAYING'
                    self.toggle_mouse(True)

            elif self.state == 'CHAPTER_SPLASH':
                if event.type in [pygame.KEYDOWN, pygame.MOUSEBUTTONDOWN]:
                    self.state = 'PLAYING'
                    self.toggle_mouse(True)

            elif self.state == 'PAUSE':
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    pos = event.pos
                    for idx, btn_r in self.ui_mgr.pause_btn_rects:
                        if btn_r.collidepoint(pos):
                            self.sound.play('ui_beep')
                            if idx == 0:  # Resume
                                self.state = 'PLAYING'
                                self.toggle_mouse(True)
                            elif idx == 1:  # Journal
                                self.state = 'JOURNAL'
                            elif idx == 2:  # Save
                                SaveSystem.save_game("manual_save", self.player, self.quest_mgr, self.level_map)
                                self.feedback_message = "Campaign saved to manual slot."
                                self.feedback_timer = 4.0
                                self.state = 'PLAYING'
                                self.toggle_mouse(True)
                            elif idx == 3:  # Load
                                if SaveSystem.load_game("manual_save", self.player, self.quest_mgr):
                                    self.load_chapter_level(self.quest_mgr.current_chapter)
                                self.state = 'PLAYING'
                                self.toggle_mouse(True)
                            elif idx == 4:  # Title
                                self.state = 'MAIN_MENU'
                            break

                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        self.state = 'PLAYING'
                        self.toggle_mouse(True)

            elif self.state == 'PROLOGUE_CUTSCENE':
                self.dialogue.handle_input(event)

            elif self.state == 'ENDING':
                if (event.type == pygame.KEYDOWN and event.key in [pygame.K_SPACE, pygame.K_RETURN, pygame.K_ESCAPE]) or \
                   (event.type == pygame.MOUSEBUTTONDOWN and event.button == 1):
                    data = self.cinematics.get_ending_data(self.selected_ending)
                    lines = data.get("cinematic_lines", [])
                    if self.ending_stage < len(lines):
                        self.ending_stage += 1
                        self.sound.play('ui_beep')
                    else:
                        self.state = 'MAIN_MENU'

    def draw(self):
        sw, sh = self.screen.get_size()

        if self.state == 'MAIN_MENU':
            self.screen.fill((10, 14, 20))
            if self.cinematics.img_corridor_cyan:
                scaled_bg = self.cinematics._get_scaled_bg(self.cinematics.img_corridor_cyan, (sw, sh))
                if scaled_bg:
                    self.screen.blit(scaled_bg, (0, 0))
                overlay = pygame.Surface((sw, sh), pygame.SRCALPHA)
                overlay.fill((8, 12, 18, 175))
                self.screen.blit(overlay, (0, 0))

            t_y = max(40, sh // 2 - 240)
            t_surf = pygame.font.SysFont("arial", 42, bold=True).render("SECTOR 9: THE LAST DIRECTIVE", True, COLOR_CYAN_GLOW)
            self.screen.blit(t_surf, (sw // 2 - t_surf.get_width() // 2, t_y))
            sub_surf = pygame.font.SysFont("arial", 18).render("Deep Space Dreadnought Adventure // UNSC Aegis-9", True, (160, 200, 225))
            self.screen.blit(sub_surf, (sw // 2 - sub_surf.get_width() // 2, t_y + 54))

            mx, my = pygame.mouse.get_pos()

            if self.credits_active:
                box_w = min(820, sw - 80)
                box_h = min(460, sh - 100)
                box = pygame.Rect((sw - box_w) // 2, (sh - box_h) // 2, box_w, box_h)
                pygame.draw.rect(self.screen, (14, 18, 26), box, border_radius=6)
                pygame.draw.rect(self.screen, COLOR_CYAN, box, 2, border_radius=6)
                self.screen.blit(self.ui_mgr.font_title.render("CREW & PRODUCTION CREDITS", True, COLOR_CYAN), (box.x + 35, box.y + 25))
                creds = [
                    "Commander Clara Voss — Systems Officer & Protagonist",
                    "Captain Elias Ward — Commander, Aegis-9",
                    "NOVA Unit 4 — Shipboard Artificial Intelligence",
                    "Chief Engineer Malik Reyes — Reactor & Systems Specialist",
                    "Dr. Sera Nahl — Veyr Quantum Physicist",
                    "THE WATCHER — The Continuum Engine Decision Matrix",
                    "Narrative Design & System Architecture — Sector 9 Python Team"
                ]
                for idx, c in enumerate(creds):
                    self.screen.blit(self.ui_mgr.font_body.render(f"//  {c}", True, COLOR_WHITE), (box.x + 35, box.y + 75 + idx * 38))
                self.screen.blit(self.ui_mgr.font_small.render("Click or press any key to return", True, COLOR_AMBER), (box.x + 35, box.bottom - 35))

            elif self.controls_active:
                box_w = min(820, sw - 80)
                box_h = min(480, sh - 100)
                box = pygame.Rect((sw - box_w) // 2, (sh - box_h) // 2, box_w, box_h)
                pygame.draw.rect(self.screen, (14, 18, 26), box, border_radius=6)
                pygame.draw.rect(self.screen, COLOR_CYAN, box, 2, border_radius=6)
                self.screen.blit(self.ui_mgr.font_title.render("TACTICAL CONTROLS & MANUAL", True, COLOR_CYAN), (box.x + 35, box.y + 25))
                ctrls = [
                    "WASD / Arrow Keys — Movement, Strafing & Navigation",
                    "Mouse — First-Person Look & Direct Clickable Tactical Interfaces",
                    "E / Left Click — Interact with Terminals, Doors, Items & Clues",
                    "F — Toggle Tactical Suit Flashlight",
                    "TAB / J — Open Mission Journal, Audio Logs & Telemetry",
                    "I — Open Inventory & Recovered Artifacts",
                    "F11 — Toggle Fullscreen / Windowed Mode",
                    "ESC — Pause Mission / Release Cursor"
                ]
                for idx, c in enumerate(ctrls):
                    self.screen.blit(self.ui_mgr.font_body.render(f"//  {c}", True, COLOR_WHITE), (box.x + 35, box.y + 75 + idx * 38))
                self.screen.blit(self.ui_mgr.font_small.render("Click or press any key to return", True, COLOR_AMBER), (box.x + 35, box.bottom - 35))

            else:
                self.menu_btn_rects = []
                btn_w = min(380, sw - 80)
                btn_h = 46
                start_y = t_y + 105
                for idx, opt in enumerate(self.menu_options):
                    my_pos = start_y + idx * 56
                    btn_rect = pygame.Rect(sw // 2 - btn_w // 2, my_pos, btn_w, btn_h)
                    self.menu_btn_rects.append((idx, btn_rect))

                    hover = btn_rect.collidepoint((mx, my))
                    bg = (28, 52, 78) if hover else (18, 24, 34)
                    border = COLOR_CYAN_GLOW if hover else (50, 75, 95)

                    pygame.draw.rect(self.screen, bg, btn_rect, border_radius=4)
                    pygame.draw.rect(self.screen, border, btn_rect, 1, border_radius=4)

                    col = COLOR_WHITE if hover else (180, 195, 210)
                    opt_surf = self.ui_mgr.font_body.render(opt, True, col)
                    self.screen.blit(opt_surf, (btn_rect.centerx - opt_surf.get_width() // 2, btn_rect.y + 12))

        elif self.state == 'PLAYING':
            theme = self.current_level.theme if self.current_level else 'bridge'
            z_buf = self.raycaster.render(self.render_surf, self.player, self.level_map, theme=theme)
            self.sprite_renderer.render_sprites(
                self.render_surf, self.sprites, self.player, z_buf,
                RENDER_WIDTH, RENDER_HEIGHT, FOV, HALF_FOV
            )

            # Smoothly stretch 3D surface to fullscreen
            scaled_3d = pygame.transform.scale(self.render_surf, (sw, sh))
            self.screen.blit(scaled_3d, (0, 0))

            # Minimap (top right)
            mw = len(self.level_map[0]) * 7 if (self.level_map and len(self.level_map) > 0) else 140
            self.raycaster.draw_minimap(self.screen, self.player, self.level_map, origin=(sw - mw - 25, 20), scale=7)

            # Objective Compass Waypoint
            obj_target = self.get_current_objective_target()

            # HUD Overlay
            self.ui_mgr.draw_hud(self.screen, self.player, self.quest_mgr, self.interaction_prompt, objective_target=obj_target)

            # Active Dialogue Subtitles
            if self.dialogue.is_active:
                self.dialogue.draw(self.screen)

            # Feedback Banner
            if self.feedback_timer > 0:
                fb_y = (sh - 180) if self.dialogue.is_active else (sh - 75)
                f_box_w = min(560, sw - 80)
                f_box = pygame.Rect((sw - f_box_w) // 2, fb_y, f_box_w, 36)
                pygame.draw.rect(self.screen, (14, 20, 30, 220), f_box, border_radius=4)
                pygame.draw.rect(self.screen, COLOR_CYAN, f_box, 1, border_radius=4)
                f_surf = self.ui_mgr.font_hud.render(self.feedback_message, True, COLOR_CYAN_GLOW)
                self.screen.blit(f_surf, (f_box.centerx - f_surf.get_width() // 2, f_box.y + 8))

        elif self.state == 'PUZZLE':
            self.active_puzzle.draw(self.screen)

        elif self.state == 'JOURNAL':
            self.ui_mgr.draw_journal(self.screen, self.player, self.quest_mgr)

        elif self.state == 'INVENTORY':
            self.ui_mgr.draw_inventory(self.screen, self.player)

        elif self.state == 'CHAPTER_SPLASH':
            info = self.quest_mgr.get_current_chapter_info()
            self.cinematics.draw_chapter_splash(
                self.screen, self.quest_mgr.current_chapter,
                info.get("title", ""), info.get("location", ""),
                info.get("main_objective", "")
            )

        elif self.state == 'PAUSE':
            self.ui_mgr.draw_pause_menu(self.screen)

        elif self.state == 'PROLOGUE_CUTSCENE':
            theme = self.current_level.theme if self.current_level else 'bridge'
            z_buf = self.raycaster.render(self.render_surf, self.player, self.level_map, theme=theme)
            self.sprite_renderer.render_sprites(
                self.render_surf, self.sprites, self.player, z_buf,
                RENDER_WIDTH, RENDER_HEIGHT, FOV, HALF_FOV
            )
            scaled_3d = pygame.transform.scale(self.render_surf, (sw, sh))
            self.screen.blit(scaled_3d, (0, 0))

            pulse = int((math.sin(self.game_timer * 4.0) + 1.0) * 25)
            overlay = pygame.Surface((sw, sh), pygame.SRCALPHA)
            overlay.fill((255, 20, 20, pulse))
            self.screen.blit(overlay, (0, 0))

            if self.dialogue.is_active:
                self.dialogue.draw(self.screen)

        elif self.state == 'MISSION_BRIEFING':
            self.cinematics.draw_backstory_briefing(self.screen, self.game_timer, audio_active=self.sound.is_voice_playing())

        elif self.state == 'ENDING':
            self.cinematics.draw_ending_screen(self.screen, self.selected_ending, self.ending_stage, self.ending_timer)

        pygame.display.flip()
