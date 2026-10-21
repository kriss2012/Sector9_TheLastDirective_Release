"""Space Lobby: pygame glue for the corridor hub (doors, locks, missions).

Rules live in `lobby_logic` / `door_system` / `lobby_layout` (pure Python, unit
tested). This module only adapts them to the engine: level building, player /
quest bridging, the keypad puzzle UI and the lockdown overlay.
"""
import math
import pygame

from src import lobby_layout as L
from src.levels import LevelData
from src.lobby_logic import LobbyLogic
from src.puzzles import BasePuzzle
from src.sprite_renderer import SpriteObject
from src.config import (
    COLOR_CYAN, COLOR_CYAN_GLOW, COLOR_ALERT_RED, COLOR_AMBER, COLOR_GREEN, COLOR_WHITE,
)

LOBBY_CHAPTER_ID = L.LOBBY_CHAPTER_ID


class LobbyState:
    """Adapts the engine's Player + QuestManager to the interface LobbyLogic expects."""

    def __init__(self, engine):
        self.engine = engine

    def has_item(self, name): return self.engine.player.has_item(name)
    def add_item(self, name): return self.engine.player.add_item(name)

    def remove_item(self, name):
        inv = self.engine.player.inventory
        if name in inv:
            inv.remove(name)

    def has_flag(self, flag): return self.engine.quest_mgr.has_flag(flag)
    def set_flag(self, flag): self.engine.quest_mgr.set_flag(flag)

    def complete(self, obj_id):
        self.engine.quest_mgr.complete_objective(obj_id, self.engine.player)

    def add_log(self, key, title): return self.engine.player.add_log(key, title)

    def say(self, message):
        self.engine.feedback_message = message
        self.engine.feedback_timer = 4.5

    def play(self, sound_name): self.engine.sound.play(sound_name)


def build_lobby_level(state=None):
    """Create the lobby LevelData. `state` (optional) restores saved progress:
    doors the player already unlocked and pickups already taken."""
    grid = L.build_grid()
    unlocked = [did for did in L.DOOR_CELLS.values()
                if state is not None and state.has_flag(f"door_unlocked:{did}")]
    doors = L.build_doors(unlocked)

    sprites = []
    for eid, stype, x, y, label, is_obj in L.SPRITES:
        if state is not None and state.has_flag(f"taken:{eid}"):
            continue
        sprites.append(SpriteObject(x, y, stype, entity_id=eid, interactive=True,
                                    label=label, is_objective=is_obj))
    for stype, x, y in L.DECOR:
        sprites.append(SpriteObject(x, y, stype, interactive=False))

    return LevelData(
        LOBBY_CHAPTER_ID, grid, L.SPAWN, 'lobby', sprites, L.build_interactions(),
        doors=doors, wall_tex_map=L.build_wall_tex_map(grid),
    )


class LobbyController:
    def __init__(self, engine, level):
        self.engine = engine
        self.level = level
        self.doors = level.doors
        self.logic = LobbyLogic(LobbyState(engine), self.doors)
        self.doors.sync_grid(engine.level_map)
        self._font = None
        self._font_small = None

    # ------------------------------------------------------------ interaction
    def prompt(self, info):
        return self.logic.prompt(info)

    def handle(self, target):
        """Handle an interaction target from GameEngine.handle_interactions().
        Returns True when the lobby consumed it."""
        if not target:
            return False
        if target[0] == "sprite":
            sp = target[1]
            result = self.logic.pickup(sp.entity_id)
            if result is None:
                return False
            if result:
                sp.active = False
            return True
        if target[0] == "coord":
            info = target[3]
            kind = info.get("type")
            if kind == "lobby_door":
                action = self.logic.interact_door(info["id"])
                if action:
                    if action["action"] == "keypad":
                        self._open_keypad(action)
                    elif action["action"] == "launch":
                        self.engine.launch_from_lobby()
                return True
            if kind == "lobby_terminal":
                self.logic.interact_terminal(info["id"])
                return True
        return False

    def _open_keypad(self, action):
        door_id = action["door_id"]
        puzzle = LobbyKeypadPuzzle(action["title"], action["code"],
                                   hint_known=self.engine.quest_mgr.has_flag(L.FLAG_ACCEPTED))
        puzzle.on_complete = lambda: self.logic.keypad_success(door_id)
        self.engine.launch_puzzle(puzzle)

    # ----------------------------------------------------------------- update
    def update(self, dt):
        p = self.engine.player
        self.logic.update(dt, (p.x, p.y))
        self.doors.sync_grid(self.engine.level_map)

    def objective_target(self):
        return self.logic.objective_target()

    # ---------------------------------------------------------------- overlay
    def draw_overlay(self, screen):
        if not self.doors.lockdown_active:
            return
        if self._font is None:
            self._font = pygame.font.SysFont("arial", 24, bold=True)
            self._font_small = pygame.font.SysFont("arial", 14, bold=True)
        sw, sh = screen.get_size()
        pulse = 0.5 + 0.5 * math.sin(self.engine.game_timer * 6.0)

        edge = pygame.Surface((sw, sh), pygame.SRCALPHA)
        pygame.draw.rect(edge, (255, 30, 30, int(60 + 90 * pulse)), (0, 0, sw, sh), 14)
        screen.blit(edge, (0, 0))

        banner = pygame.Rect(sw // 2 - 230, 104, 460, 56)
        pygame.draw.rect(screen, (40, 10, 14), banner, border_radius=5)
        pygame.draw.rect(screen, COLOR_ALERT_RED, banner, 2, border_radius=5)
        title = self._font.render("CONTAINMENT LOCKDOWN", True, COLOR_ALERT_RED if pulse > 0.4 else COLOR_AMBER)
        screen.blit(title, (banner.centerx - title.get_width() // 2, banner.y + 6))
        secs = self.logic.lockdown_remaining
        sub = self._font_small.render(f"ALL BULKHEADS SEALED - RELEASE IN {secs:04.1f}s", True, COLOR_WHITE)
        screen.blit(sub, (banner.centerx - sub.get_width() // 2, banner.y + 34))


class LobbyKeypadPuzzle(BasePuzzle):
    """Keypad lock for code doors. After 3 wrong codes the pad locks out briefly."""

    MAX_TRIES = 3
    LOCKOUT_SECONDS = 4.0

    def __init__(self, door_label, code, hint_known=False):
        clue = (f"Override code issued by the Mission Board [{code}]" if hint_known
                else "Code not on record - accept the mission at the Mission Control board first")
        super().__init__(f"{door_label} // KEYPAD LOCK",
                         f"Enter the {len(code)}-digit override code.", clue)
        self.target_code = code
        self.entered_code = ""
        self.tries = 0
        self.lockout = 0.0
        self.on_complete = None
        self.keypad_rects = {}
        self.btn_clr_rect = pygame.Rect(0, 0, 0, 0)
        self.btn_ent_rect = pygame.Rect(0, 0, 0, 0)

    def update(self, dt):
        super().update(dt)
        if self.lockout > 0:
            self.lockout = max(0.0, self.lockout - dt)

    def _press(self, digit):
        if self.lockout > 0 or len(self.entered_code) >= len(self.target_code):
            return
        self.entered_code += digit
        self.sound.play('ui_beep')
        if len(self.entered_code) == len(self.target_code):
            self._check_code()

    def _check_code(self):
        if self.lockout > 0:
            return
        if self.entered_code == self.target_code:
            self.is_completed = True
            self.result_code = True
            self.set_feedback("CODE ACCEPTED. DOOR UNLOCKED.", COLOR_GREEN)
            self.sound.play('access_granted')
            return
        self.tries += 1
        self.entered_code = ""
        self.sound.play('access_denied')
        if self.tries >= self.MAX_TRIES:
            self.tries = 0
            self.lockout = self.LOCKOUT_SECONDS
            self.set_feedback(f"KEYPAD LOCKED OUT - RETRY IN {int(self.LOCKOUT_SECONDS)}s", COLOR_ALERT_RED,
                              self.LOCKOUT_SECONDS)
        else:
            self.set_feedback(f"INVALID CODE ({self.MAX_TRIES - self.tries} ATTEMPTS LEFT)", COLOR_ALERT_RED)

    def handle_input(self, event):
        if self.check_common_click(event):
            return
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for digit, rect in self.keypad_rects.items():
                if rect.collidepoint(event.pos):
                    self._press(digit)
                    return
            if self.btn_clr_rect.collidepoint(event.pos):
                self.entered_code = ""
                self.sound.play('ui_beep')
            elif self.btn_ent_rect.collidepoint(event.pos):
                self._check_code()
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_BACKSPACE:
                self.entered_code = self.entered_code[:-1]
                self.sound.play('ui_beep')
            elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                self._check_code()
            elif event.unicode.isdigit():
                self._press(event.unicode)

    def draw(self, surface):
        frame = self.draw_frame(surface)
        mx, my = pygame.mouse.get_pos()

        lx, ly = frame.x + 40, frame.y + 65
        surface.blit(self.font_title.render("DOOR CONTROLLER", True, COLOR_CYAN), (lx, ly))
        for i, line in enumerate((self.description,
                                  "Three wrong codes lock the pad out",
                                  f"for {int(self.LOCKOUT_SECONDS)} seconds.")):
            surface.blit(self.font_body.render(line, True, COLOR_WHITE), (lx, ly + 40 + i * 24))
        status = "LOCKED OUT" if self.lockout > 0 else "AWAITING CODE"
        surface.blit(self.font_body.render(f"STATUS: {status}", True,
                                           COLOR_ALERT_RED if self.lockout > 0 else COLOR_AMBER), (lx, ly + 130))

        rx, ry = frame.x + 440, frame.y + 65
        disp = pygame.Rect(rx, ry + 20, 240, 46)
        pygame.draw.rect(surface, (10, 20, 30), disp, border_radius=4)
        pygame.draw.rect(surface, COLOR_ALERT_RED if self.lockout > 0 else COLOR_CYAN, disp, 2, border_radius=4)
        shown = self.entered_code.ljust(len(self.target_code), "_")
        code_surf = pygame.font.SysFont("arial", 26, bold=True).render(f"CODE: {shown}", True, COLOR_CYAN_GLOW)
        surface.blit(code_surf, (disp.centerx - code_surf.get_width() // 2, disp.y + 6))

        layout = [["1", "2", "3"], ["4", "5", "6"], ["7", "8", "9"], ["CLR", "0", "ENT"]]
        bw, bh = 70, 42
        for r, row in enumerate(layout):
            for c, key in enumerate(row):
                rect = pygame.Rect(rx + c * (bw + 14), ry + 80 + r * (bh + 10), bw, bh)
                hover = rect.collidepoint((mx, my))
                border = COLOR_CYAN_GLOW if hover else (50, 80, 110)
                if key == "CLR":
                    self.btn_clr_rect = rect
                    border = COLOR_ALERT_RED if hover else (130, 40, 40)
                elif key == "ENT":
                    self.btn_ent_rect = rect
                    border = COLOR_GREEN if hover else (30, 120, 60)
                else:
                    self.keypad_rects[key] = rect
                pygame.draw.rect(surface, (30, 52, 74) if hover else (18, 26, 38), rect, border_radius=4)
                pygame.draw.rect(surface, border, rect, 2, border_radius=4)
                lbl = self.font_body.render(key, True, COLOR_WHITE)
                surface.blit(lbl, (rect.centerx - lbl.get_width() // 2, rect.centery - 10))
