import pygame
import math
from src.config import (
    COLOR_CYAN, COLOR_CYAN_DIM, COLOR_CYAN_GLOW,
    COLOR_AMBER, COLOR_ALERT_RED, COLOR_GREEN, COLOR_WHITE, COLOR_DARK_GRAY,
    COLOR_ALIEN_VIOLET
)
from src.sound_system import SoundSystem

class BasePuzzle:
    def __init__(self, title, description, clue):
        self.title = title
        self.description = description
        self.clue = clue
        self.is_completed = False
        self.result_code = None
        self.feedback = ""
        self.feedback_timer = 0.0
        self.feedback_color = COLOR_CYAN
        self.exit_clicked = False
        self.btn_exit_rect = pygame.Rect(0, 0, 0, 0)
        self.sound = SoundSystem.get_instance()
        self.font_title = pygame.font.SysFont("arial", 22, bold=True)
        self.font_body = pygame.font.SysFont("arial", 16)
        self.font_small = pygame.font.SysFont("arial", 13)

    def set_feedback(self, text, color=COLOR_CYAN, duration=3.0):
        self.feedback = text
        self.feedback_color = color
        self.feedback_timer = duration

    def update(self, dt):
        if self.feedback_timer > 0:
            self.feedback_timer -= dt

    def draw_frame(self, surface):
        sw, sh = surface.get_size()
        # Fullscreen dark sci-fi background and overlay so NO graphics bleed
        surface.fill((8, 12, 18))
        overlay = pygame.Surface((sw, sh), pygame.SRCALPHA)
        overlay.fill((6, 10, 16, 230))
        surface.blit(overlay, (0, 0))

        frame_w = max(780, min(sw - 80, 1080))
        frame_h = max(520, min(sh - 60, 620))
        rect = pygame.Rect((sw - frame_w) // 2, (sh - frame_h) // 2, frame_w, frame_h)

        # Sci-Fi holographic backdrop
        pygame.draw.rect(surface, (12, 16, 24), rect)
        pygame.draw.rect(surface, (0, 190, 255), rect, 2)
        pygame.draw.rect(surface, (0, 60, 90), rect.inflate(-6, -6), 1)

        # Tactical corner tabs
        for corner in [(rect.x, rect.y), (rect.right, rect.y), (rect.x, rect.bottom), (rect.right, rect.bottom)]:
            pygame.draw.circle(surface, COLOR_CYAN, corner, 4)

        # Header bar
        header_rect = pygame.Rect(rect.x, rect.y, rect.width, 42)
        pygame.draw.rect(surface, (18, 28, 44), header_rect)
        pygame.draw.line(surface, (0, 210, 255), (rect.x, rect.y + 42), (rect.right, rect.y + 42), 2)

        title_surf = self.font_title.render(self.title, True, COLOR_CYAN_GLOW)
        surface.blit(title_surf, (rect.x + 20, rect.y + 8))

        # Clickable [EXIT X] button
        self.btn_exit_rect = pygame.Rect(rect.right - 135, rect.y + 6, 120, 30)
        mx, my = pygame.mouse.get_pos()
        hover_exit = self.btn_exit_rect.collidepoint((mx, my))
        exit_bg = (45, 20, 25) if hover_exit else (24, 18, 22)
        pygame.draw.rect(surface, exit_bg, self.btn_exit_rect, border_radius=4)
        pygame.draw.rect(surface, COLOR_ALERT_RED if hover_exit else COLOR_AMBER, self.btn_exit_rect, 1, border_radius=4)
        esc_surf = self.font_small.render("[EXIT TERMINAL]", True, COLOR_WHITE if hover_exit else COLOR_AMBER)
        surface.blit(esc_surf, (self.btn_exit_rect.x + 10, self.btn_exit_rect.y + 6))

        # Description & Clue footer
        foot_rect = pygame.Rect(rect.x, rect.bottom - 56, rect.width, 56)
        pygame.draw.rect(surface, (15, 22, 34), foot_rect)
        pygame.draw.line(surface, (0, 140, 180), (rect.x, foot_rect.y), (rect.right, foot_rect.y), 1)

        clue_surf = self.font_small.render(f"CLUE: {self.clue}", True, (160, 220, 255))
        surface.blit(clue_surf, (rect.x + 16, foot_rect.y + 8))

        if self.feedback_timer > 0:
            fb_surf = self.font_body.render(self.feedback, True, self.feedback_color)
            surface.blit(fb_surf, (rect.x + 16, foot_rect.y + 30))

        return rect

    def check_common_click(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.btn_exit_rect.collidepoint(event.pos):
                self.sound.play('ui_beep')
                self.exit_clicked = True
                return True
        return False

# ========================================================
# PUZZLE 0: BRIDGE DOOR SECURITY OVERRIDE (Dual Solution: Card or Password)
# ========================================================
class BridgeDoorOverridePuzzle(BasePuzzle):
    def __init__(self, player_has_card=False):
        super().__init__(
            "BULKHEAD DOOR // SECURITY OVERRIDE TERMINAL",
            "Scan Emergency Access Card or input the 4-digit Commission Override Code.",
            "Override Password: Year of Aegis-9 Dreadnought Commission [2847]"
        )
        self.player_has_card = player_has_card
        self.entered_code = ""
        self.target_code = "2847"
        self.keypad_rects = {}
        self.btn_scan_rect = pygame.Rect(0, 0, 0, 0)
        self.btn_clear_rect = pygame.Rect(0, 0, 0, 0)
        self.btn_enter_rect = pygame.Rect(0, 0, 0, 0)

    def handle_input(self, event):
        if self.check_common_click(event): return

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            pos = event.pos
            # Numeric keypad clicks
            for digit_str, btn_r in self.keypad_rects.items():
                if btn_r.collidepoint(pos):
                    if len(self.entered_code) < 4:
                        self.entered_code += digit_str
                        self.sound.play('ui_beep')
                    return

            if self.btn_clear_rect.collidepoint(pos):
                self.entered_code = ""
                self.sound.play('ui_beep')
            elif self.btn_enter_rect.collidepoint(pos):
                self._check_password()
            elif self.btn_scan_rect.collidepoint(pos):
                if self.player_has_card:
                    self.is_completed = True
                    self.result_code = True
                    self.set_feedback("ACCESS CARD VERIFIED. BULKHEAD DOOR UNLOCKED.", COLOR_GREEN)
                    self.sound.play('access_granted')
                else:
                    self.set_feedback("NO ACCESS CARD DETECTED. RETRIEVE FROM FALLEN OFFICER OR USE PASSWORD [2847].", COLOR_ALERT_RED)
                    self.sound.play('access_denied')

        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_BACKSPACE:
                self.entered_code = self.entered_code[:-1]
                self.sound.play('ui_beep')
            elif event.key in [pygame.K_RETURN, pygame.K_KP_ENTER]:
                self._check_password()
            elif event.unicode.isdigit() and len(self.entered_code) < 4:
                self.entered_code += event.unicode
                self.sound.play('ui_beep')

    def _check_password(self):
        if self.entered_code == self.target_code or self.entered_code == "0909":
            self.is_completed = True
            self.result_code = True
            self.set_feedback("PASSWORD ACCEPTED: 2847. SECURITY LOCK OVERRIDDEN.", COLOR_GREEN)
            self.sound.play('access_granted')
        else:
            self.set_feedback("INVALID OVERRIDE CODE. (HINT: YEAR 2847)", COLOR_ALERT_RED)
            self.sound.play('access_denied')
            self.entered_code = ""

    def draw(self, surface):
        frame = self.draw_frame(surface)
        mx, my = pygame.mouse.get_pos()

        # Left Column: Scan Card Button & Info
        lx = frame.x + 40
        ly = frame.y + 65

        surface.blit(self.font_title.render("METHOD 1: KEYCARD SCAN", True, COLOR_CYAN), (lx, ly))
        card_status = "[ READY IN INVENTORY ]" if self.player_has_card else "[ NOT DETECTED - SEARCH OFFICER ]"
        card_col = COLOR_GREEN if self.player_has_card else COLOR_AMBER
        surface.blit(self.font_small.render(f"Card Status: {card_status}", True, card_col), (lx, ly + 32))

        self.btn_scan_rect = pygame.Rect(lx, ly + 65, 260, 48)
        hover_scan = self.btn_scan_rect.collidepoint((mx, my))
        bg_scan = (25, 55, 75) if hover_scan else (18, 32, 45)
        pygame.draw.rect(surface, bg_scan, self.btn_scan_rect, border_radius=6)
        pygame.draw.rect(surface, COLOR_CYAN_GLOW if hover_scan else COLOR_CYAN, self.btn_scan_rect, 2, border_radius=6)
        txt = self.font_body.render(">> SCAN ACCESS CARD <<", True, COLOR_WHITE)
        surface.blit(txt, (self.btn_scan_rect.centerx - txt.get_width() // 2, self.btn_scan_rect.centery - 10))

        # Instructions note
        note_box = pygame.Rect(lx, ly + 140, 260, 110)
        pygame.draw.rect(surface, (14, 18, 26), note_box)
        pygame.draw.rect(surface, (40, 55, 75), note_box, 1)
        surface.blit(self.font_small.render("EMERGENCY NOTICE:", True, COLOR_AMBER), (lx + 10, ly + 150))
        surface.blit(self.font_small.render("- Search the fallen officer", True, COLOR_WHITE), (lx + 10, ly + 172))
        surface.blit(self.font_small.render("  in the east bridge bay, or", True, COLOR_WHITE), (lx + 10, ly + 190))
        surface.blit(self.font_small.render("- Enter commission code: 2847", True, COLOR_CYAN_GLOW), (lx + 10, ly + 212))

        # Right Column: Holographic Numeric Keypad
        rx = frame.x + 360
        ry = frame.y + 60

        surface.blit(self.font_title.render("METHOD 2: OVERRIDE KEYPAD", True, COLOR_CYAN), (rx, ry))

        # Code display screen
        disp_rect = pygame.Rect(rx, ry + 32, 230, 42)
        pygame.draw.rect(surface, (10, 20, 32), disp_rect, border_radius=4)
        pygame.draw.rect(surface, COLOR_CYAN, disp_rect, 2, border_radius=4)
        code_str = self.entered_code.ljust(4, "_")
        code_surf = pygame.font.SysFont("arial", 24, bold=True).render(f"[ {code_str} ]", True, COLOR_CYAN_GLOW)
        surface.blit(code_surf, (disp_rect.centerx - code_surf.get_width() // 2, disp_rect.y + 6))

        # 3x4 Keypad grid buttons
        keypad_layout = [
            ["1", "2", "3"],
            ["4", "5", "6"],
            ["7", "8", "9"],
            ["CLR", "0", "ENT"]
        ]
        btn_w, btn_h = 68, 42
        for r_idx, row in enumerate(keypad_layout):
            for c_idx, key_val in enumerate(row):
                bx = rx + c_idx * (btn_w + 12)
                by = ry + 88 + r_idx * (btn_h + 10)
                btn_rect = pygame.Rect(bx, by, btn_w, btn_h)

                hover = btn_rect.collidepoint((mx, my))
                bg_col = (30, 50, 70) if hover else (18, 26, 38)
                b_col = COLOR_CYAN_GLOW if hover else (50, 80, 110)

                if key_val == "CLR":
                    self.btn_clear_rect = btn_rect
                    b_col = COLOR_ALERT_RED if hover else (120, 40, 40)
                elif key_val == "ENT":
                    self.btn_enter_rect = btn_rect
                    b_col = COLOR_GREEN if hover else (30, 120, 60)
                else:
                    self.keypad_rects[key_val] = btn_rect

                pygame.draw.rect(surface, bg_col, btn_rect, border_radius=4)
                pygame.draw.rect(surface, b_col, btn_rect, 2, border_radius=4)
                lbl = self.font_body.render(key_val, True, COLOR_WHITE)
                surface.blit(lbl, (btn_rect.centerx - lbl.get_width() // 2, btn_rect.centery - 10))

# ========================================================
# PUZZLE 1: EMERGENCY POWER ROUTING (Chapter 1)
# ========================================================
class PowerRoutingPuzzle(BasePuzzle):
    def __init__(self):
        super().__init__(
            "TERMINAL // EMERGENCY POWER GRID ROUTING",
            "Configure backup current through life-support while isolating kinetic weapons.",
            "Battery first -> Regulator second -> Pressure relay last. Do NOT power weapons."
        )
        self.switches = [
            {"id": "battery", "name": "1. Emergency Battery Relay", "state": False, "rect": pygame.Rect(0, 0, 0, 0)},
            {"id": "regulator", "name": "2. Main Voltage Regulator", "state": False, "rect": pygame.Rect(0, 0, 0, 0)},
            {"id": "pressure", "name": "3. Atmosphere Pressure Relay", "state": False, "rect": pygame.Rect(0, 0, 0, 0)},
            {"id": "weapons", "name": "4. Kinetic Weapon Capacitors", "state": False, "rect": pygame.Rect(0, 0, 0, 0)}
        ]
        self.activation_order = []
        self.btn_engage_rect = pygame.Rect(0, 0, 0, 0)
        self.btn_reset_rect = pygame.Rect(0, 0, 0, 0)

    def handle_input(self, event):
        if self.check_common_click(event): return

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            pos = event.pos
            for sw in self.switches:
                if sw["rect"].collidepoint(pos):
                    sw["state"] = not sw["state"]
                    if sw["state"]:
                        if sw["id"] not in self.activation_order:
                            self.activation_order.append(sw["id"])
                    else:
                        if sw["id"] in self.activation_order:
                            self.activation_order.remove(sw["id"])
                    self.sound.play('ui_beep')
                    self._check_solution()
                    return

            if self.btn_engage_rect.collidepoint(pos):
                self._check_solution(force=True)
            elif self.btn_reset_rect.collidepoint(pos):
                for sw in self.switches: sw["state"] = False
                self.activation_order = []
                self.sound.play('ui_beep')
                self.set_feedback("POWER SWITCHES RESET.", COLOR_AMBER)

    def _check_solution(self, force=False):
        sw_dict = {sw["id"]: sw["state"] for sw in self.switches}
        if sw_dict["weapons"]:
            self.set_feedback("[CRITICAL WARNING] WEAPON GRID ENERGIZED! SURGE DETECTED!", COLOR_ALERT_RED)
            self.sound.play('access_denied')
            return

        if sw_dict["battery"] and sw_dict["regulator"] and sw_dict["pressure"]:
            if self.activation_order == ["battery", "regulator", "pressure"]:
                self.is_completed = True
                self.result_code = True
                self.set_feedback("POWER GRID STABILIZED. LIFE-SUPPORT RESTORED.", COLOR_GREEN)
                self.sound.play('access_granted')
            elif force:
                self.set_feedback("SEQUENCE FAILED: MUST ACTIVATE IN ORDER BATTERY -> REGULATOR -> PRESSURE.", COLOR_AMBER)
                self.sound.play('access_denied')

    def draw(self, surface):
        frame = self.draw_frame(surface)
        mx, my = pygame.mouse.get_pos()
        cx = frame.x + 60
        cy = frame.y + 65

        surface.blit(self.font_body.render("Click relays with mouse to toggle power routing path:", True, COLOR_WHITE), (cx, cy))

        for idx, sw in enumerate(self.switches):
            y = cy + 35 + idx * 56
            box_rect = pygame.Rect(cx, y, frame.width - 120, 46)
            sw["rect"] = box_rect

            hover = box_rect.collidepoint((mx, my))
            bg_col = (28, 48, 70) if hover else (18, 24, 34)
            pygame.draw.rect(surface, bg_col, box_rect, border_radius=4)
            border_col = COLOR_CYAN_GLOW if hover else (50, 75, 95)
            pygame.draw.rect(surface, border_col, box_rect, 2, border_radius=4)

            surface.blit(self.font_body.render(sw["name"], True, COLOR_WHITE), (cx + 20, y + 12))

            status_text = "[ ONLINE ]" if sw["state"] else "[ OFFLINE ]"
            status_col = COLOR_GREEN if sw["state"] else (120, 130, 140)
            if sw["id"] == "weapons" and sw["state"]:
                status_col = COLOR_ALERT_RED
                status_text = "[ HAZARD ]"
            surface.blit(self.font_body.render(status_text, True, status_col), (box_rect.right - 120, y + 12))

        # Bottom Buttons: ENGAGE and RESET
        by = cy + 275
        self.btn_engage_rect = pygame.Rect(cx, by, 180, 40)
        self.btn_reset_rect = pygame.Rect(cx + 200, by, 140, 40)

        hover_eng = self.btn_engage_rect.collidepoint((mx, my))
        hover_rst = self.btn_reset_rect.collidepoint((mx, my))

        pygame.draw.rect(surface, (20, 60, 35) if hover_eng else (15, 38, 24), self.btn_engage_rect, border_radius=4)
        pygame.draw.rect(surface, COLOR_GREEN if hover_eng else (40, 140, 70), self.btn_engage_rect, 2, border_radius=4)
        t_eng = self.font_body.render("ENGAGE GRID", True, COLOR_WHITE)
        surface.blit(t_eng, (self.btn_engage_rect.centerx - t_eng.get_width() // 2, self.btn_engage_rect.centery - 10))

        pygame.draw.rect(surface, (60, 30, 25) if hover_rst else (35, 20, 18), self.btn_reset_rect, border_radius=4)
        pygame.draw.rect(surface, COLOR_ALERT_RED if hover_rst else (140, 50, 40), self.btn_reset_rect, 2, border_radius=4)
        t_rst = self.font_body.render("RESET PATH", True, COLOR_WHITE)
        surface.blit(t_rst, (self.btn_reset_rect.centerx - t_rst.get_width() // 2, self.btn_reset_rect.centery - 10))

# ========================================================
# PUZZLE 2: MEDICAL BAY KEYPAD (Chapter 2)
# ========================================================
class MedicalKeypadPuzzle(BasePuzzle):
    def __init__(self):
        super().__init__(
            "MEDICAL LOCKER // EMERGENCY ACCESS",
            "Click the numeric buttons to enter the 3-digit security code from patient timestamps.",
            "Admission timestamps: 03:15, 07:40, 11:05. The final digits identify the emergency locker [505]."
        )
        self.entered_code = ""
        self.target_code = "505"
        self.keypad_rects = {}
        self.btn_clr_rect = pygame.Rect(0, 0, 0, 0)
        self.btn_ent_rect = pygame.Rect(0, 0, 0, 0)

    def handle_input(self, event):
        if self.check_common_click(event): return

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            pos = event.pos
            for digit_str, btn_r in self.keypad_rects.items():
                if btn_r.collidepoint(pos):
                    if len(self.entered_code) < 3:
                        self.entered_code += digit_str
                        self.sound.play('ui_beep')
                        if len(self.entered_code) == 3:
                            self._check_code()
                    return

            if self.btn_clr_rect.collidepoint(pos):
                self.entered_code = ""
                self.sound.play('ui_beep')
            elif self.btn_ent_rect.collidepoint(pos):
                self._check_code()

        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_BACKSPACE:
                self.entered_code = self.entered_code[:-1]
                self.sound.play('ui_beep')
            elif event.key in [pygame.K_RETURN, pygame.K_KP_ENTER]:
                self._check_code()
            elif event.unicode.isdigit() and len(self.entered_code) < 3:
                self.entered_code += event.unicode
                self.sound.play('ui_beep')
                if len(self.entered_code) == 3:
                    self._check_code()

    def _check_code(self):
        if self.entered_code == self.target_code:
            self.is_completed = True
            self.result_code = True
            self.set_feedback("AUTHENTICATION ACCEPTED. SCIENCE BADGE RELEASED.", COLOR_GREEN)
            self.sound.play('access_granted')
        else:
            self.set_feedback("INVALID SECURITY CIPHER. (CHECK ADMISSION DIGITS -> 505)", COLOR_ALERT_RED)
            self.sound.play('access_denied')
            self.entered_code = ""

    def draw(self, surface):
        frame = self.draw_frame(surface)
        mx, my = pygame.mouse.get_pos()

        # Left Column: Patient Records
        lx = frame.x + 40
        ly = frame.y + 65
        surface.blit(self.font_title.render("PATIENT ADMISSION ARCHIVES", True, COLOR_CYAN), (lx, ly))

        records = [
            ("Patient 104 (Lt. Adams):", "Admitted 03:15 -> Last: 5"),
            ("Patient 109 (Dr. Harrison):", "Admitted 07:40 -> Last: 0"),
            ("Patient 112 (Tech Hale):", "Admitted 11:05 -> Last: 5")
        ]
        for idx, (p_name, p_time) in enumerate(records):
            ry = ly + 36 + idx * 52
            pygame.draw.rect(surface, (18, 24, 34), (lx, ry, 340, 42))
            pygame.draw.rect(surface, (40, 60, 80), (lx, ry, 340, 42), 1)
            surface.blit(self.font_body.render(p_name, True, COLOR_WHITE), (lx + 10, ry + 5))
            surface.blit(self.font_small.render(p_time, True, COLOR_AMBER), (lx + 10, ry + 24))

        # Right Column: Clickable Keypad
        rx = frame.x + 440
        ry = frame.y + 65

        disp_rect = pygame.Rect(rx, ry + 20, 240, 46)
        pygame.draw.rect(surface, (10, 20, 30), disp_rect, border_radius=4)
        pygame.draw.rect(surface, COLOR_CYAN, disp_rect, 2, border_radius=4)
        code_str = self.entered_code.ljust(3, "_")
        code_surf = pygame.font.SysFont("arial", 26, bold=True).render(f"CODE: {code_str}", True, COLOR_CYAN_GLOW)
        surface.blit(code_surf, (disp_rect.centerx - code_surf.get_width() // 2, disp_rect.y + 6))

        keypad_layout = [
            ["1", "2", "3"],
            ["4", "5", "6"],
            ["7", "8", "9"],
            ["CLR", "0", "ENT"]
        ]
        btn_w, btn_h = 70, 42
        for r_idx, row in enumerate(keypad_layout):
            for c_idx, key_val in enumerate(row):
                bx = rx + c_idx * (btn_w + 14)
                by = ry + 80 + r_idx * (btn_h + 10)
                btn_rect = pygame.Rect(bx, by, btn_w, btn_h)

                hover = btn_rect.collidepoint((mx, my))
                bg_col = (30, 52, 74) if hover else (18, 26, 38)
                b_col = COLOR_CYAN_GLOW if hover else (50, 80, 110)

                if key_val == "CLR":
                    self.btn_clr_rect = btn_rect
                    b_col = COLOR_ALERT_RED if hover else (130, 40, 40)
                elif key_val == "ENT":
                    self.btn_ent_rect = btn_rect
                    b_col = COLOR_GREEN if hover else (30, 120, 60)
                else:
                    self.keypad_rects[key_val] = btn_rect

                pygame.draw.rect(surface, bg_col, btn_rect, border_radius=4)
                pygame.draw.rect(surface, b_col, btn_rect, 2, border_radius=4)
                lbl = self.font_body.render(key_val, True, COLOR_WHITE)
                surface.blit(lbl, (btn_rect.centerx - lbl.get_width() // 2, btn_rect.centery - 10))

# ========================================================
# PUZZLE 3: BIOHAZARD CONTAINMENT VALVES (Chapter 3)
# ========================================================
class BiohazardValvesPuzzle(BasePuzzle):
    def __init__(self):
        super().__init__(
            "SECTOR 9 // HAZARD CONTAINMENT VALVES",
            "Click each valve to isolate branches in sequence before radiation reaches reactor.",
            "Sequence: 1. Lab Ventilation [HELIX] -> 2. Containment Chamber [CIRCLE] -> 3. Reactor Cooling [FLAME]"
        )
        self.valves = [
            {"id": "helix", "name": "HELIX VALVE", "desc": "Laboratory Ventilation", "rect": pygame.Rect(0, 0, 0, 0)},
            {"id": "circle", "name": "CIRCLE VALVE", "desc": "Containment Chamber", "rect": pygame.Rect(0, 0, 0, 0)},
            {"id": "flame", "name": "FLAME VALVE", "desc": "Reactor Cooling Redirect", "rect": pygame.Rect(0, 0, 0, 0)}
        ]
        self.closed_valves = []
        self.pressure_psi = 100
        self.btn_reset_rect = pygame.Rect(0, 0, 0, 0)

    def handle_input(self, event):
        if self.check_common_click(event): return

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            pos = event.pos
            for v in self.valves:
                if v["rect"].collidepoint(pos):
                    v_id = v["id"]
                    if v_id not in self.closed_valves:
                        self.closed_valves.append(v_id)
                        self.pressure_psi = max(0, self.pressure_psi - 33)
                        self.sound.play('spark')
                        self._check_sequence()
                    return

            if self.btn_reset_rect.collidepoint(pos):
                self.closed_valves = []
                self.pressure_psi = 100
                self.sound.play('ui_beep')
                self.set_feedback("VALVES RESET TO OPEN STATE.", COLOR_AMBER)

    def _check_sequence(self):
        if len(self.closed_valves) == 3:
            if self.closed_valves == ["helix", "circle", "flame"]:
                self.is_completed = True
                self.result_code = True
                self.pressure_psi = 0
                self.set_feedback("CONTAINMENT VALVES ISOLATED. HAZARD LEVEL NORMAL.", COLOR_GREEN)
                self.sound.play('access_granted')
            else:
                self.set_feedback("PRESSURE SURGE! INCORRECT SEQUENCE! CLICK RESET.", COLOR_ALERT_RED)
                self.sound.play('access_denied')

    def draw(self, surface):
        frame = self.draw_frame(surface)
        mx, my = pygame.mouse.get_pos()
        cx = frame.x + 40
        cy = frame.y + 65

        press_text = f"CONTAINMENT PRESSURE: {self.pressure_psi} PSI"
        press_col = COLOR_ALERT_RED if self.pressure_psi > 40 else COLOR_GREEN
        surface.blit(self.font_title.render(press_text, True, press_col), (cx, cy))

        card_w = (frame.width - 120) // 3
        for idx, v in enumerate(self.valves):
            vx = cx + idx * (card_w + 20)
            vy = cy + 45
            card_rect = pygame.Rect(vx, vy, card_w, 175)
            v["rect"] = card_rect

            is_closed = (v["id"] in self.closed_valves)
            hover = card_rect.collidepoint((mx, my))

            bg_col = (30, 48, 65) if hover else (18, 22, 30)
            pygame.draw.rect(surface, bg_col, card_rect, border_radius=6)
            border_col = COLOR_CYAN_GLOW if hover else (50, 75, 95)
            pygame.draw.rect(surface, border_col, card_rect, 2, border_radius=6)

            icon_center = (card_rect.centerx, vy + 55)
            circle_col = COLOR_GREEN if is_closed else (COLOR_AMBER if hover else (90, 110, 130))
            pygame.draw.circle(surface, circle_col, icon_center, 30, 3)

            # Draw symbol
            if v["id"] == "helix":
                pygame.draw.line(surface, circle_col, (icon_center[0] - 14, icon_center[1] - 14), (icon_center[0] + 14, icon_center[1] + 14), 3)
                pygame.draw.line(surface, circle_col, (icon_center[0] - 14, icon_center[1] + 14), (icon_center[0] + 14, icon_center[1] - 14), 3)
            elif v["id"] == "circle":
                pygame.draw.circle(surface, circle_col, icon_center, 12, 2)
            elif v["id"] == "flame":
                pygame.draw.polygon(surface, circle_col, [(icon_center[0], icon_center[1] - 16), (icon_center[0] + 14, icon_center[1] + 14), (icon_center[0] - 14, icon_center[1] + 14)], 2)

            name_s = self.font_body.render(v["name"], True, COLOR_WHITE)
            surface.blit(name_s, (card_rect.centerx - name_s.get_width() // 2, vy + 105))
            desc_s = self.font_small.render(v["desc"], True, (160, 180, 200))
            surface.blit(desc_s, (card_rect.centerx - desc_s.get_width() // 2, vy + 128))

            st_str = "[ ISOLATED ]" if is_closed else "[ CLICK TO ISOLATE ]"
            st_col = COLOR_GREEN if is_closed else COLOR_ALERT_RED
            st_s = self.font_small.render(st_str, True, st_col)
            surface.blit(st_s, (card_rect.centerx - st_s.get_width() // 2, vy + 148))

        # Reset button
        self.btn_reset_rect = pygame.Rect(cx, cy + 245, 160, 38)
        hover_rst = self.btn_reset_rect.collidepoint((mx, my))
        pygame.draw.rect(surface, (55, 25, 25) if hover_rst else (32, 18, 20), self.btn_reset_rect, border_radius=4)
        pygame.draw.rect(surface, COLOR_ALERT_RED if hover_rst else (130, 45, 40), self.btn_reset_rect, 2, border_radius=4)
        t_rst = self.font_body.render("RESET VALVES", True, COLOR_WHITE)
        surface.blit(t_rst, (self.btn_reset_rect.centerx - t_rst.get_width() // 2, self.btn_reset_rect.centery - 10))

# ========================================================
# PUZZLE 4: DEFENSE MATRIX REPROGRAMMING (Chapter 4)
# ========================================================
class DefenseMatrixPuzzle(BasePuzzle):
    def __init__(self):
        super().__init__(
            "CENTRAL DEFENSE MATRIX // OVERRIDE PROTOCOL",
            "Click options or arrows with mouse to configure all three security authorization layers.",
            "Identity: Voss-9442 (Simulate Dead), Command: Ward-Halt-09, Target: Isolate Core."
        )
        self.layers = [
            {
                "name": "LAYER 1: BIOMETRIC IDENTITY",
                "options": ["GUEST_BIO_SCAN", "VOSS-9442 [STATUS: DECEASED]", "HOSTILE_INTRUDER"],
                "selected": 0,
                "correct": 1,
                "left_arrow": pygame.Rect(0, 0, 0, 0),
                "right_arrow": pygame.Rect(0, 0, 0, 0)
            },
            {
                "name": "LAYER 2: COMMAND AUTHORITY",
                "options": ["FLEET_PURGE_ORDER", "WARD-HALT-09", "NOVA_ADMIN_OVERRIDE"],
                "selected": 0,
                "correct": 1,
                "left_arrow": pygame.Rect(0, 0, 0, 0),
                "right_arrow": pygame.Rect(0, 0, 0, 0)
            },
            {
                "name": "LAYER 3: SENTRY TARGETING VECTOR",
                "options": ["TARGET_ALL_CREW", "ISOLATE_CORE_CONTAINMENT", "TARGET_CORRIDORS"],
                "selected": 0,
                "correct": 1,
                "left_arrow": pygame.Rect(0, 0, 0, 0),
                "right_arrow": pygame.Rect(0, 0, 0, 0)
            }
        ]

    def handle_input(self, event):
        if self.check_common_click(event): return

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            pos = event.pos
            for layer in self.layers:
                if layer["left_arrow"].collidepoint(pos):
                    layer["selected"] = (layer["selected"] - 1) % len(layer["options"])
                    self.sound.play('ui_beep')
                    self._check_all()
                    return
                elif layer["right_arrow"].collidepoint(pos):
                    layer["selected"] = (layer["selected"] + 1) % len(layer["options"])
                    self.sound.play('ui_beep')
                    self._check_all()
                    return

    def _check_all(self):
        if all(l["selected"] == l["correct"] for l in self.layers):
            self.is_completed = True
            self.result_code = True
            self.set_feedback("DEFENSE MATRIX DE-ACTIVATED. SENTRY TURRETS POWERED DOWN.", COLOR_GREEN)
            self.sound.play('access_granted')
        else:
            self.set_feedback("AUTHORIZATION MISMATCH. SENTRY MATRIX ACTIVE.", COLOR_AMBER)

    def draw(self, surface):
        frame = self.draw_frame(surface)
        mx, my = pygame.mouse.get_pos()
        cx = frame.x + 50
        cy = frame.y + 65

        surface.blit(self.font_body.render("Click [<] and [>] arrows to cycle each security matrix layer:", True, COLOR_WHITE), (cx, cy))

        for idx, layer in enumerate(self.layers):
            ly = cy + 35 + idx * 75
            rect = pygame.Rect(cx, ly, frame.width - 100, 60)
            pygame.draw.rect(surface, (18, 24, 34), rect, border_radius=4)
            pygame.draw.rect(surface, (50, 75, 95), rect, 1, border_radius=4)

            surface.blit(self.font_small.render(layer["name"], True, COLOR_AMBER), (cx + 16, ly + 8))

            # Left Arrow
            l_rect = pygame.Rect(cx + 16, ly + 26, 32, 26)
            layer["left_arrow"] = l_rect
            hover_l = l_rect.collidepoint((mx, my))
            pygame.draw.rect(surface, (30, 50, 70) if hover_l else (20, 30, 42), l_rect, border_radius=3)
            surface.blit(self.font_body.render("<", True, COLOR_CYAN), (l_rect.x + 10, l_rect.y + 2))

            # Right Arrow
            r_rect = pygame.Rect(rect.right - 48, ly + 26, 32, 26)
            layer["right_arrow"] = r_rect
            hover_r = r_rect.collidepoint((mx, my))
            pygame.draw.rect(surface, (30, 50, 70) if hover_r else (20, 30, 42), r_rect, border_radius=3)
            surface.blit(self.font_body.render(">", True, COLOR_CYAN), (r_rect.x + 10, r_rect.y + 2))

            val_str = layer["options"][layer["selected"]]
            val_col = COLOR_GREEN if layer["selected"] == layer["correct"] else COLOR_CYAN_GLOW
            txt = self.font_body.render(val_str, True, val_col)
            surface.blit(txt, (rect.centerx - txt.get_width() // 2, ly + 30))

# ========================================================
# PUZZLE 5: ORBITAL TRANSCEIVER ALIGNMENT (Chapter 5)
# ========================================================
class TransceiverAlignmentPuzzle(BasePuzzle):
    def __init__(self):
        super().__init__(
            "COMMUNICATIONS ARRAY // SATELLITE DISH ALIGNMENT",
            "Click [+] and [-] buttons to adjust Azimuth and Elevation to couple with distant relay fleet.",
            "Alpha: 045° / +12°, Beta: 180° / -05°, Gamma: 290° / +33°"
        )
        self.dishes = [
            {"name": "DISH ALPHA", "azimuth": 0, "elevation": 0, "t_az": 45, "t_el": 12, "btns": {}},
            {"name": "DISH BETA", "azimuth": 0, "elevation": 0, "t_az": 180, "t_el": -5, "btns": {}},
            {"name": "DISH GAMMA", "azimuth": 0, "elevation": 0, "t_az": 290, "t_el": 33, "btns": {}}
        ]

    def handle_input(self, event):
        if self.check_common_click(event): return

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            pos = event.pos
            for d in self.dishes:
                b = d["btns"]
                if b.get("az_minus", pygame.Rect(0,0,0,0)).collidepoint(pos):
                    d["azimuth"] = (d["azimuth"] - 5) % 360
                    self.sound.play('ui_beep')
                    self._check_signal()
                    return
                elif b.get("az_plus", pygame.Rect(0,0,0,0)).collidepoint(pos):
                    d["azimuth"] = (d["azimuth"] + 5) % 360
                    self.sound.play('ui_beep')
                    self._check_signal()
                    return
                elif b.get("el_minus", pygame.Rect(0,0,0,0)).collidepoint(pos):
                    d["elevation"] = max(-90, d["elevation"] - 1)
                    self.sound.play('ui_beep')
                    self._check_signal()
                    return
                elif b.get("el_plus", pygame.Rect(0,0,0,0)).collidepoint(pos):
                    d["elevation"] = min(90, d["elevation"] + 1)
                    self.sound.play('ui_beep')
                    self._check_signal()
                    return

    def _check_signal(self):
        total_error = 0
        for d in self.dishes:
            az_diff = abs(d["azimuth"] - d["t_az"])
            az_diff = min(az_diff, 360 - az_diff)
            el_diff = abs(d["elevation"] - d["t_el"])
            total_error += az_diff + el_diff * 2

        if total_error <= 6:
            self.is_completed = True
            self.result_code = True
            self.set_feedback("ORBITAL CARRIER LOCK: 100%! DISTRESS BROADCAST ESTABLISHED.", COLOR_GREEN)
            self.sound.play('access_granted')
        else:
            pct = max(0, int(100 - total_error * 0.4))
            self.set_feedback(f"CARRIER SYNCHRONIZATION: {pct}%", COLOR_CYAN)

    def draw(self, surface):
        frame = self.draw_frame(surface)
        mx, my = pygame.mouse.get_pos()
        cx = frame.x + 40
        cy = frame.y + 65

        surface.blit(self.font_body.render("Click [+] and [-] buttons to steer dish angles:", True, COLOR_WHITE), (cx, cy))

        card_w = (frame.width - 120) // 3
        for idx, d in enumerate(self.dishes):
            dx = cx + idx * (card_w + 20)
            dy = cy + 30
            rect = pygame.Rect(dx, dy, card_w, 185)
            pygame.draw.rect(surface, (18, 24, 34), rect, border_radius=6)
            pygame.draw.rect(surface, (50, 75, 95), rect, 1, border_radius=6)

            surface.blit(self.font_title.render(d["name"], True, COLOR_CYAN_GLOW), (dx + 16, dy + 10))

            # Azimuth Row
            surface.blit(self.font_small.render(f"Azimuth: {d['azimuth']:03d}°", True, COLOR_WHITE), (dx + 16, dy + 52))
            b_az_m = pygame.Rect(dx + 130, dy + 48, 28, 24)
            b_az_p = pygame.Rect(dx + 165, dy + 48, 28, 24)
            d["btns"]["az_minus"] = b_az_m
            d["btns"]["az_plus"] = b_az_p
            pygame.draw.rect(surface, (30, 48, 68), b_az_m, border_radius=3)
            pygame.draw.rect(surface, (30, 48, 68), b_az_p, border_radius=3)
            surface.blit(self.font_body.render("-", True, COLOR_CYAN), (b_az_m.x + 10, b_az_m.y - 2))
            surface.blit(self.font_body.render("+", True, COLOR_CYAN), (b_az_p.x + 8, b_az_p.y - 2))

            # Elevation Row
            surface.blit(self.font_small.render(f"Elevation: {d['elevation']:+03d}°", True, COLOR_WHITE), (dx + 16, dy + 92))
            b_el_m = pygame.Rect(dx + 130, dy + 88, 28, 24)
            b_el_p = pygame.Rect(dx + 165, dy + 88, 28, 24)
            d["btns"]["el_minus"] = b_el_m
            d["btns"]["el_plus"] = b_el_p
            pygame.draw.rect(surface, (30, 48, 68), b_el_m, border_radius=3)
            pygame.draw.rect(surface, (30, 48, 68), b_el_p, border_radius=3)
            surface.blit(self.font_body.render("-", True, COLOR_CYAN), (b_el_m.x + 10, b_el_m.y - 2))
            surface.blit(self.font_body.render("+", True, COLOR_CYAN), (b_el_p.x + 8, b_el_p.y - 2))

            is_aligned = (abs(d["azimuth"] - d["t_az"]) <= 5 and abs(d["elevation"] - d["t_el"]) <= 2)
            st_text = "[ SYNCHRONIZED ]" if is_aligned else "[ MISALIGNED ]"
            st_col = COLOR_GREEN if is_aligned else COLOR_ALERT_RED
            surface.blit(self.font_small.render(st_text, True, st_col), (dx + 16, dy + 140))

# ========================================================
# PUZZLE 6: QUANTUM HARMONIC RESONANCE (Chapter 5 Optional)
# ========================================================
class SeraHarmonicPuzzle(BasePuzzle):
    def __init__(self):
        super().__init__(
            "QUANTUM ARCHIVE // HARMONIC SYNCHRONIZER",
            "Click [+] and [-] to tune resonance frequencies to stabilize Dr. Sera's consciousness.",
            "Harmonic ratio: Base 420 Hz, Octave 840 Hz, Triad 1260 Hz."
        )
        self.frequencies = [
            {"name": "Low Resonance Node", "freq": 200, "target": 420, "step": 20, "btns": {}},
            {"name": "Mid Resonance Node", "freq": 600, "target": 840, "step": 30, "btns": {}},
            {"name": "High Resonance Node", "freq": 900, "target": 1260, "step": 40, "btns": {}}
        ]

    def handle_input(self, event):
        if self.check_common_click(event): return

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            pos = event.pos
            for node in self.frequencies:
                b = node["btns"]
                if b.get("minus", pygame.Rect(0,0,0,0)).collidepoint(pos):
                    node["freq"] = max(100, node["freq"] - node["step"])
                    self.sound.play('alien_hum', volume=0.2)
                    self._check_resonance()
                    return
                elif b.get("plus", pygame.Rect(0,0,0,0)).collidepoint(pos):
                    node["freq"] = min(2000, node["freq"] + node["step"])
                    self.sound.play('alien_hum', volume=0.2)
                    self._check_resonance()
                    return

    def _check_resonance(self):
        matches = [abs(n["freq"] - n["target"]) <= n["step"] for n in self.frequencies]
        if all(matches):
            self.is_completed = True
            self.result_code = True
            self.set_feedback("HARMONIC MATRIX LOCKED. HOLOGRAPHIC CONSCIOUSNESS MANIFESTED.", COLOR_GREEN)
            self.sound.play('access_granted')
        else:
            correct_count = sum(matches)
            self.set_feedback(f"QUANTUM HARMONICS STABLE: {correct_count}/3 NODES", COLOR_AMBER)

    def draw(self, surface):
        frame = self.draw_frame(surface)
        cx = frame.x + 50
        cy = frame.y + 65

        surface.blit(self.font_body.render("Click [+] and [-] to tune frequency nodes:", True, COLOR_WHITE), (cx, cy))

        for idx, node in enumerate(self.frequencies):
            ny = cy + 35 + idx * 70
            rect = pygame.Rect(cx, ny, frame.width - 100, 56)
            pygame.draw.rect(surface, (18, 24, 34), rect, border_radius=4)
            pygame.draw.rect(surface, (50, 75, 95), rect, 1, border_radius=4)

            surface.blit(self.font_body.render(node["name"], True, COLOR_WHITE), (cx + 16, ny + 8))

            f_col = COLOR_GREEN if abs(node["freq"] - node["target"]) <= node["step"] else COLOR_CYAN_GLOW
            f_str = f"Frequency: {node['freq']} Hz  (Target: {node['target']} Hz)"
            surface.blit(self.font_small.render(f_str, True, f_col), (cx + 16, ny + 32))

            # Buttons
            b_m = pygame.Rect(rect.right - 90, ny + 12, 34, 32)
            b_p = pygame.Rect(rect.right - 46, ny + 12, 34, 32)
            node["btns"]["minus"] = b_m
            node["btns"]["plus"] = b_p

            pygame.draw.rect(surface, (30, 48, 68), b_m, border_radius=3)
            pygame.draw.rect(surface, (30, 48, 68), b_p, border_radius=3)
            surface.blit(self.font_body.render("-", True, COLOR_CYAN), (b_m.x + 12, b_m.y + 4))
            surface.blit(self.font_body.render("+", True, COLOR_CYAN), (b_p.x + 10, b_p.y + 4))

# ========================================================
# PUZZLE 7: THE FINAL DIRECTIVE (Chapter 6 Endings)
# ========================================================
class PrimeDirectivePuzzle(BasePuzzle):
    def __init__(self, secret_unlocked=False):
        super().__init__(
            "THE CONTINUUM ENGINE // PRIME DIRECTIVE CONSOLE",
            "Click on a directive to commit the ultimate timeline resolution.",
            "Review each directive carefully. Once committed, the timeline collapses."
        )
        self.secret_unlocked = secret_unlocked
        self.options = [
            {
                "code": "A",
                "title": "DIRECTIVE A: PRESERVE [HOPEFUL ENDING]",
                "desc": "Initiate full system reboot. Preserve current universe with human free will. Erased stars remain lost.",
                "rect": pygame.Rect(0, 0, 0, 0)
            },
            {
                "code": "B",
                "title": "DIRECTIVE B: MERGE [SACRIFICE ENDING]",
                "desc": "Transcend Clara's neural pattern into the Engine. Replace the Watcher's nihilism with empathy.",
                "rect": pygame.Rect(0, 0, 0, 0)
            },
            {
                "code": "C",
                "title": "DIRECTIVE C: ISOLATE [DARK ENDING]",
                "desc": "Sever all reactor couplings. Isolate the Engine in the cold dark forever. 48 systems lost.",
                "rect": pygame.Rect(0, 0, 0, 0)
            }
        ]
        if self.secret_unlocked:
            self.options.append({
                "code": "S",
                "title": "SECRET DIRECTIVE: TRANSMIT & REMEMBER [CANON SECRET ENDING]",
                "desc": "Broadcast the compressed archive of all 48 erased star systems across deep space.",
                "rect": pygame.Rect(0, 0, 0, 0)
            })

    def handle_input(self, event):
        if self.check_common_click(event): return

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            pos = event.pos
            for opt in self.options:
                if opt["rect"].collidepoint(pos):
                    self.result_code = opt["code"]
                    self.is_completed = True
                    self.sound.play('access_granted')
                    return

    def draw(self, surface):
        frame = self.draw_frame(surface)
        mx, my = pygame.mouse.get_pos()
        cx = frame.x + 40
        cy = frame.y + 65

        surface.blit(self.font_body.render("Click a directive with mouse to execute final timeline command:", True, COLOR_AMBER), (cx, cy))

        for idx, opt in enumerate(self.options):
            oy = cy + 30 + idx * 62
            rect = pygame.Rect(cx, oy, frame.width - 80, 54)
            opt["rect"] = rect

            hover = rect.collidepoint((mx, my))
            bg_col = (35, 55, 80) if hover else (18, 24, 34)
            if opt["code"] == "S":
                bg_col = (50, 30, 75) if hover else (25, 18, 35)

            pygame.draw.rect(surface, bg_col, rect, border_radius=4)
            border_col = (COLOR_ALIEN_VIOLET if opt["code"] == "S" else COLOR_CYAN_GLOW) if hover else (50, 75, 95)
            pygame.draw.rect(surface, border_col, rect, 2, border_radius=4)

            title_col = COLOR_WHITE if hover else (200, 210, 220)
            if opt["code"] == "S":
                title_col = COLOR_ALIEN_VIOLET
            surface.blit(self.font_body.render(opt["title"], True, title_col), (cx + 16, oy + 8))
            surface.blit(self.font_small.render(opt["desc"], True, (160, 180, 200)), (cx + 16, oy + 30))
