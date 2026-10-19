import pygame
import os
import json
import math
from src.config import (
    COLOR_CYAN, COLOR_CYAN_GLOW, COLOR_ALERT_RED, COLOR_AMBER,
    COLOR_GREEN, COLOR_WHITE, COLOR_DARK_GRAY, DATA_DIR
)
from src.sound_system import SoundSystem

class UIManager:
    def __init__(self):
        self.sound = SoundSystem.get_instance()
        self.font_title = pygame.font.SysFont("arial", 22, bold=True)
        self.font_hud = pygame.font.SysFont("arial", 15, bold=True)
        self.font_body = pygame.font.SysFont("arial", 15)
        self.font_small = pygame.font.SysFont("arial", 13)

        self.lore_data = {}
        lore_path = os.path.join(DATA_DIR, "lore_logs.json")
        if os.path.exists(lore_path):
            with open(lore_path, 'r', encoding='utf-8') as f:
                self.lore_data = json.load(f)

        self.journal_tab = 0
        self.selected_log_idx = 0
        self.pause_selected_idx = 0

        # Clickable rects
        self.journal_tab_rects = []
        self.journal_log_rects = []
        self.btn_close_journal_rect = pygame.Rect(0, 0, 0, 0)
        self.btn_close_inv_rect = pygame.Rect(0, 0, 0, 0)
        self.pause_btn_rects = []

    # ========================================================
    # IN-GAME SCI-FI HUD WITH COMPASS WAYPOINT
    # ========================================================
    def draw_hud(self, surface, player, quest_manager, interaction_prompt="", objective_target=None):
        sw, sh = surface.get_size()
        ch_info = quest_manager.get_current_chapter_info()
        deck_name = ch_info.get("deck", "AEGIS-9 WARSHIP")
        main_obj = quest_manager.get_main_objective()

        # Top Header Bar
        top_bar = pygame.Rect(20, 14, sw - 40, 44)
        pygame.draw.rect(surface, (12, 16, 24), top_bar, border_radius=4)
        pygame.draw.rect(surface, (0, 190, 255), top_bar, 1, border_radius=4)

        deck_surf = self.font_hud.render(deck_name, True, COLOR_CYAN_GLOW)
        surface.blit(deck_surf, (top_bar.x + 16, top_bar.y + 12))

        # Objective Banner
        obj_text = f"DIRECTIVE: {main_obj}"
        obj_surf = self.font_body.render(obj_text, True, COLOR_WHITE)
        surface.blit(obj_surf, (top_bar.x + 280, top_bar.y + 12))

        # Dynamic 3D Waypoint Compass
        if objective_target:
            tx, ty, tname = objective_target
            dx = tx - player.x
            dy = ty - player.y
            dist = math.hypot(dx, dy)
            target_angle = math.atan2(dy, dx)
            diff_angle = (target_angle - player.angle + math.pi) % (2 * math.pi) - math.pi

            if abs(diff_angle) < 0.35:
                direction_arrow = "▲ STRAIGHT AHEAD"
            elif diff_angle > 0:
                direction_arrow = "▶ TURN RIGHT"
            else:
                direction_arrow = "◀ TURN LEFT"

            compass_rect = pygame.Rect(sw // 2 - 180, 64, 360, 28)
            pygame.draw.rect(surface, (15, 22, 34, 210), compass_rect, border_radius=4)
            pygame.draw.rect(surface, COLOR_AMBER, compass_rect, 1, border_radius=4)
            comp_txt = f"NAV: {tname} [{dist:.1f}m] {direction_arrow}"
            c_surf = self.font_small.render(comp_txt, True, (255, 220, 100))
            surface.blit(c_surf, (compass_rect.centerx - c_surf.get_width() // 2, compass_rect.y + 6))

        # Bottom Left: Suit Integrity & Flashlight Battery
        panel_w = 280
        panel_h = 78
        panel_rect = pygame.Rect(20, sh - panel_h - 16, panel_w, panel_h)
        pygame.draw.rect(surface, (12, 16, 24), panel_rect, border_radius=4)
        pygame.draw.rect(surface, (0, 150, 200), panel_rect, 1, border_radius=4)

        # Suit Integrity Bar
        hp_pct = max(0.0, min(1.0, player.health / player.max_health))
        hp_col = COLOR_GREEN if hp_pct > 0.4 else COLOR_ALERT_RED
        surface.blit(self.font_small.render(f"SUIT INTEGRITY: {int(player.health)}%", True, hp_col), (panel_rect.x + 14, panel_rect.y + 8))
        pygame.draw.rect(surface, (28, 32, 42), (panel_rect.x + 14, panel_rect.y + 26, 250, 8), border_radius=2)
        pygame.draw.rect(surface, hp_col, (panel_rect.x + 14, panel_rect.y + 26, int(250 * hp_pct), 8), border_radius=2)

        # Flashlight Battery Bar
        bat_pct = max(0.0, min(1.0, player.flashlight_battery / player.max_flashlight))
        bat_col = COLOR_CYAN if player.flashlight_on else (120, 140, 150)
        bat_status = "ON" if player.flashlight_on else "OFF"
        surface.blit(self.font_small.render(f"FLASHLIGHT [{bat_status}]: {int(player.flashlight_battery)}% [F]", True, bat_col), (panel_rect.x + 14, panel_rect.y + 40))
        pygame.draw.rect(surface, (28, 32, 42), (panel_rect.x + 14, panel_rect.y + 60, 250, 6), border_radius=2)
        pygame.draw.rect(surface, bat_col, (panel_rect.x + 14, panel_rect.y + 60, int(250 * bat_pct), 6), border_radius=2)

        # Center: Interactive Prompt
        if interaction_prompt:
            p_w = min(420, max(280, len(interaction_prompt) * 11 + 30))
            prompt_rect = pygame.Rect(sw // 2 - p_w // 2, sh // 2 + 40, p_w, 40)
            pygame.draw.rect(surface, (14, 22, 34), prompt_rect, border_radius=4)
            pygame.draw.rect(surface, COLOR_AMBER, prompt_rect, 2, border_radius=4)
            p_surf = self.font_hud.render(interaction_prompt, True, COLOR_AMBER)
            surface.blit(p_surf, (prompt_rect.centerx - p_surf.get_width() // 2, prompt_rect.y + 10))

        # Bottom Right: Key bindings reference
        keys_surf = self.font_small.render("[TAB] Journal  [I] Inventory  [ESC] Pause  [F11] Fullscreen", True, (150, 175, 200))
        surface.blit(keys_surf, (sw - keys_surf.get_width() - 25, sh - 28))

    # ========================================================
    # IN-GAME JOURNAL MODAL (TAB / J) — FULLY MOUSE CLICKABLE
    # ========================================================
    def draw_journal(self, surface, player, quest_manager):
        sw, sh = surface.get_size()
        # Full-screen ambient dimming overlay
        overlay = pygame.Surface((sw, sh), pygame.SRCALPHA)
        overlay.fill((6, 9, 14, 215))
        surface.blit(overlay, (0, 0))

        modal_w = max(720, min(sw - 80, 1140))
        modal_h = max(520, min(sh - 80, 680))
        modal = pygame.Rect((sw - modal_w) // 2, (sh - modal_h) // 2, modal_w, modal_h)

        pygame.draw.rect(surface, (12, 16, 24), modal, border_radius=6)
        pygame.draw.rect(surface, COLOR_CYAN, modal, 2, border_radius=6)

        mx, my = pygame.mouse.get_pos()

        # Close [X] Button
        self.btn_close_journal_rect = pygame.Rect(modal.right - 45, modal.y + 8, 35, 30)
        hover_x = self.btn_close_journal_rect.collidepoint((mx, my))
        pygame.draw.rect(surface, (60, 25, 25) if hover_x else (30, 20, 25), self.btn_close_journal_rect, border_radius=3)
        pygame.draw.rect(surface, COLOR_ALERT_RED, self.btn_close_journal_rect, 1, border_radius=3)
        surface.blit(self.font_hud.render("X", True, COLOR_WHITE), (self.btn_close_journal_rect.x + 12, self.btn_close_journal_rect.y + 5))

        # Header Tabs
        tab_names = ["1. MISSION DIRECTIVES", "2. ARCHIVE RECORDINGS", "3. WARSHIP TELEMETRY"]
        self.journal_tab_rects = []
        for idx, tname in enumerate(tab_names):
            tx = modal.x + 20 + idx * 240
            t_rect = pygame.Rect(tx, modal.y + 8, 230, 36)
            self.journal_tab_rects.append(t_rect)

            is_active = (idx == self.journal_tab)
            hover_tab = t_rect.collidepoint((mx, my))
            bg = (28, 48, 72) if (is_active or hover_tab) else (16, 22, 32)
            pygame.draw.rect(surface, bg, t_rect, border_radius=4)
            border = COLOR_CYAN_GLOW if is_active else (COLOR_CYAN if hover_tab else (50, 75, 95))
            pygame.draw.rect(surface, border, t_rect, 1, border_radius=4)
            surface.blit(self.font_small.render(tname, True, COLOR_WHITE if is_active else (150, 175, 195)), (tx + 14, modal.y + 16))

        # Tab 0: Objectives List
        if self.journal_tab == 0:
            objectives = quest_manager.get_objectives()
            surface.blit(self.font_title.render("CHAPTER DIRECTIVES & PROGRESSION", True, COLOR_CYAN), (modal.x + 30, modal.y + 60))
            for idx, obj in enumerate(objectives):
                oy = modal.y + 105 + idx * 46
                box_rect = pygame.Rect(modal.x + 30, oy, modal.width - 60, 38)
                pygame.draw.rect(surface, (18, 24, 34), box_rect, border_radius=3)
                pygame.draw.rect(surface, (45, 65, 85), box_rect, 1, border_radius=3)

                is_done = obj.get("completed", False)
                chk_icon = "[X]" if is_done else "[ ]"
                chk_col = COLOR_GREEN if is_done else COLOR_AMBER
                surface.blit(self.font_hud.render(chk_icon, True, chk_col), (modal.x + 45, oy + 8))

                req_str = "" if obj.get("required", True) else "(Optional) "
                title_col = COLOR_WHITE if not is_done else (140, 180, 150)
                surface.blit(self.font_body.render(f"{req_str}{obj['text']}", True, title_col), (modal.x + 90, oy + 8))

        # Tab 1: Discovered Audio Logs
        elif self.journal_tab == 1:
            surface.blit(self.font_title.render("DISCOVERED AUDIO LOGS & SHIP ARCHIVES", True, COLOR_CYAN), (modal.x + 30, modal.y + 60))
            logs_list = list(player.discovered_logs)
            self.journal_log_rects = []
            if not logs_list:
                surface.blit(self.font_body.render("No audio recordings recovered yet. Inspect terminals and data chips in the sector.", True, (160, 170, 190)), (modal.x + 30, modal.y + 110))
            else:
                # Left Column: Clickable Log Titles
                for idx, log_k in enumerate(logs_list[:8]):
                    ly = modal.y + 105 + idx * 42
                    rect = pygame.Rect(modal.x + 30, ly, 300, 34)
                    self.journal_log_rects.append((idx, rect))

                    is_sel = (idx == self.selected_log_idx)
                    hover_log = rect.collidepoint((mx, my))
                    log_item = self.lore_data.get(log_k, {"title": log_k, "content": "Transcript missing."})

                    bg = (28, 50, 72) if (is_sel or hover_log) else (18, 22, 30)
                    pygame.draw.rect(surface, bg, rect, border_radius=3)
                    pygame.draw.rect(surface, COLOR_CYAN if is_sel else (50, 75, 95), rect, 1, border_radius=3)
                    surface.blit(self.font_small.render(log_item["title"], True, COLOR_WHITE), (rect.x + 12, rect.y + 8))

                # Right Column: Selected Log Content
                if self.selected_log_idx < len(logs_list):
                    cur_key = logs_list[self.selected_log_idx]
                    cur_log = self.lore_data.get(cur_key, {"title": cur_key, "content": "Transcript missing."})
                    cont_rect = pygame.Rect(modal.x + 350, modal.y + 105, modal.width - 380, modal.height - 140)
                    pygame.draw.rect(surface, (16, 20, 28), cont_rect, border_radius=4)
                    pygame.draw.rect(surface, (0, 140, 185), cont_rect, 1, border_radius=4)

                    surface.blit(self.font_hud.render(cur_log["title"], True, COLOR_AMBER), (cont_rect.x + 16, cont_rect.y + 14))
                    category = cur_log.get("category", "General Recording")
                    surface.blit(self.font_small.render(f"Classification: {category}", True, COLOR_CYAN), (cont_rect.x + 16, cont_rect.y + 38))

                    words = cur_log["content"].split(" ")
                    lines = []
                    cur_line = ""
                    for w in words:
                        test_l = f"{cur_line} {w}".strip()
                        if self.font_body.size(test_l)[0] < cont_rect.width - 32:
                            cur_line = test_l
                        else:
                            lines.append(cur_line)
                            cur_line = w
                    if cur_line: lines.append(cur_line)

                    for l_idx, line_str in enumerate(lines[:14]):
                        surface.blit(self.font_body.render(line_str, True, COLOR_WHITE), (cont_rect.x + 16, cont_rect.y + 68 + l_idx * 22))

        # Tab 2: Warship Telemetry
        else:
            surface.blit(self.font_title.render("AEGIS-9 TECHNICAL STATUS & ANOMALY SENSORS", True, COLOR_CYAN), (modal.x + 30, modal.y + 60))
            stats = [
                ("Vessel Registry:", "UNSC AEGIS-9 (Heavy Command Dreadnought, 4km Class)"),
                ("Operational State:", "CRITICAL DEFENSE EMERGENCY - SPATIAL DISTORTION IN SECTOR 9"),
                ("Atmosphere Status:", "Life-support stabilized via manual relay override"),
                ("Causal Stability:", "DIVERGENT TIMELINES DETECTED - 48 SYSTEMS ABSENT FROM CHARTS"),
                ("Primary AI Status:", "NOVA Unit 4 - Contradictory memory buffers detected")
            ]
            for idx, (lbl, val) in enumerate(stats):
                sy = modal.y + 115 + idx * 56
                surface.blit(self.font_hud.render(lbl, True, COLOR_AMBER), (modal.x + 30, sy))
                surface.blit(self.font_body.render(val, True, COLOR_WHITE), (modal.x + 30, sy + 24))

    # ========================================================
    # INVENTORY MODAL (I) — FULLY MOUSE CLICKABLE
    # ========================================================
    def draw_inventory(self, surface, player):
        sw, sh = surface.get_size()
        # Full-screen ambient dimming overlay
        overlay = pygame.Surface((sw, sh), pygame.SRCALPHA)
        overlay.fill((6, 9, 14, 215))
        surface.blit(overlay, (0, 0))

        modal_w = max(600, min(sw - 100, 880))
        modal_h = max(420, min(sh - 100, 560))
        modal = pygame.Rect((sw - modal_w) // 2, (sh - modal_h) // 2, modal_w, modal_h)

        pygame.draw.rect(surface, (12, 16, 24), modal, border_radius=6)
        pygame.draw.rect(surface, COLOR_CYAN, modal, 2, border_radius=6)

        mx, my = pygame.mouse.get_pos()

        # Close [X] Button
        self.btn_close_inv_rect = pygame.Rect(modal.right - 45, modal.y + 8, 35, 30)
        hover_x = self.btn_close_inv_rect.collidepoint((mx, my))
        pygame.draw.rect(surface, (60, 25, 25) if hover_x else (30, 20, 25), self.btn_close_inv_rect, border_radius=3)
        pygame.draw.rect(surface, COLOR_ALERT_RED, self.btn_close_inv_rect, 1, border_radius=3)
        surface.blit(self.font_hud.render("X", True, COLOR_WHITE), (self.btn_close_inv_rect.x + 12, self.btn_close_inv_rect.y + 5))

        surface.blit(self.font_title.render("EQUIPMENT & RECOVERED ARTIFACTS", True, COLOR_CYAN_GLOW), (modal.x + 30, modal.y + 25))

        if not player.inventory:
            surface.blit(self.font_body.render("No special items in inventory.", True, (160, 180, 200)), (modal.x + 30, modal.y + 80))
        else:
            for idx, item in enumerate(player.inventory):
                iy = modal.y + 75 + idx * 48
                rect = pygame.Rect(modal.x + 30, iy, modal.width - 60, 38)
                pygame.draw.rect(surface, (18, 26, 36), rect, border_radius=4)
                pygame.draw.rect(surface, (0, 160, 220), rect, 1, border_radius=4)
                surface.blit(self.font_body.render(f"[ITEM]  {item}", True, COLOR_WHITE), (rect.x + 16, rect.y + 8))

    # ========================================================
    # PAUSE MENU (ESC) — FULLY MOUSE CLICKABLE
    # ========================================================
    def draw_pause_menu(self, surface):
        sw, sh = surface.get_size()
        overlay = pygame.Surface((sw, sh), pygame.SRCALPHA)
        overlay.fill((8, 12, 18, 220))
        surface.blit(overlay, (0, 0))

        menu_w = 380
        menu_h = 340
        menu_rect = pygame.Rect(sw // 2 - menu_w // 2, sh // 2 - menu_h // 2, menu_w, menu_h)
        pygame.draw.rect(surface, (14, 18, 26), menu_rect, border_radius=6)
        pygame.draw.rect(surface, COLOR_CYAN, menu_rect, 2, border_radius=6)

        title = self.font_title.render("MISSION PAUSED", True, COLOR_CYAN_GLOW)
        surface.blit(title, (menu_rect.centerx - title.get_width() // 2, menu_rect.y + 25))

        mx, my = pygame.mouse.get_pos()
        options = ["RESUME MISSION", "OPEN JOURNAL (TAB)", "SAVE GAME", "LOAD GAME", "QUIT TO TITLE"]
        self.pause_btn_rects = []

        for idx, opt in enumerate(options):
            oy = menu_rect.y + 85 + idx * 46
            btn_rect = pygame.Rect(menu_rect.x + 30, oy, menu_w - 60, 36)
            self.pause_btn_rects.append((idx, btn_rect))

            is_sel = (idx == self.pause_selected_idx)
            hover = btn_rect.collidepoint((mx, my))

            bg = (28, 50, 75) if (is_sel or hover) else (18, 22, 30)
            pygame.draw.rect(surface, bg, btn_rect, border_radius=4)
            border = COLOR_CYAN_GLOW if (is_sel or hover) else (50, 75, 95)
            pygame.draw.rect(surface, border, btn_rect, 1, border_radius=4)

            opt_col = COLOR_WHITE if (is_sel or hover) else (180, 190, 200)
            opt_surf = self.font_body.render(opt, True, opt_col)
            surface.blit(opt_surf, (btn_rect.centerx - opt_surf.get_width() // 2, btn_rect.y + 7))
