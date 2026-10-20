import pygame
import os
import json
import math
from src.config import (
    COLOR_CYAN, COLOR_CYAN_GLOW,
    COLOR_ALERT_RED, COLOR_AMBER, COLOR_GREEN, COLOR_WHITE, COLOR_ALIEN_VIOLET,
    IMAGES_DIR, DATA_DIR
)
from src.sound_system import SoundSystem

class CinematicsManager:
    def __init__(self):
        self.sound = SoundSystem.get_instance()
        self.font_title = pygame.font.SysFont("arial", 28, bold=True)
        self.font_body = pygame.font.SysFont("arial", 18)
        self.font_quote = pygame.font.SysFont("arial", 16, italic=True)
        self.font_small = pygame.font.SysFont("arial", 14)
        self._scaled_cache = {}

        # Preload concept art images
        self.img_bridge_emergency = self._load_image("bridge_emergency.jpg")
        self.img_corridor_cyan = self._load_image("corridor_cyan.jpg")
        self.img_holo_terminal = self._load_image("holo_terminal.jpg")
        self.img_corridor_drone = self._load_image("corridor_drone.png")

        # Load endings data
        self.endings_data = {}
        endings_path = os.path.join(DATA_DIR, "endings.json")
        if os.path.exists(endings_path):
            with open(endings_path, 'r', encoding='utf-8') as f:
                self.endings_data = json.load(f)

    def _load_image(self, name):
        p = os.path.join(IMAGES_DIR, name)
        if os.path.exists(p):
            try:
                img = pygame.image.load(p)
                if pygame.display.get_surface() is not None:
                    img = img.convert()
                return img
            except Exception as e:
                print(f"[Cinematics] Error loading image {name}: {e}")
        return None

    def _get_scaled_bg(self, img, target_size):
        if img is None:
            return None
        cache_key = (id(img), target_size)
        if cache_key not in self._scaled_cache:
            self._scaled_cache[cache_key] = pygame.transform.scale(img, target_size)
        return self._scaled_cache[cache_key]

    # ========================================================
    # PROLOGUE OPENING CINEMATIC
    # ========================================================
    def run_prologue_cutscene(self, screen, clock, dialogue_mgr, on_finish):
        """Runs the dramatic opening sequence of Aegis-9 detecting the star vanishing."""
        self.sound.play('radio_burst')
        dialogue_mgr.start_dialogue_by_id("prologue", "scene_0_1", lambda: self._prologue_phase_2(screen, clock, dialogue_mgr, on_finish))

    def _prologue_phase_2(self, screen, clock, dialogue_mgr, on_finish):
        # Impossible transmission dialogue
        self.sound.play('drone_alert')
        dialogue_mgr.start_dialogue_by_id("prologue", "scene_0_2", lambda: self._prologue_phase_3(screen, clock, dialogue_mgr, on_finish))

    def _prologue_phase_3(self, screen, clock, dialogue_mgr, on_finish):
        self.sound.play('spark')
        dialogue_mgr.start_dialogue_by_id("prologue", "scene_0_3_start", on_finish)

    def draw_prologue_background(self, surface, time_val):
        sw, sh = surface.get_size()
        surface.fill((10, 8, 14))
        if self.img_bridge_emergency:
            scaled = self._get_scaled_bg(self.img_bridge_emergency, (sw, sh))
            if scaled:
                surface.blit(scaled, (0, 0))
            # Emergency pulsing red overlay across full screen
            pulse = int((math.sin(time_val * 4.0) + 1.0) * 35)
            overlay = pygame.Surface((sw, sh), pygame.SRCALPHA)
            overlay.fill((255, 0, 0, pulse))
            surface.blit(overlay, (0, 0))

    # ========================================================
    # MISSION BRIEFING & BACKSTORY SCREEN
    # ========================================================
    def draw_backstory_briefing(self, surface, time_val, audio_active=True):
        sw, sh = surface.get_size()
        surface.fill((8, 12, 18))

        # Background: Emergency Bridge Concept Art
        if self.img_bridge_emergency:
            scaled = self._get_scaled_bg(self.img_bridge_emergency, (sw, sh))
            if scaled:
                surface.blit(scaled, (0, 0))

        # Darkened high-tech glassmorphism overlay
        dark = pygame.Surface((sw, sh), pygame.SRCALPHA)
        dark.fill((10, 14, 22, 215))
        surface.blit(dark, (0, 0))

        # Main Briefing Frame
        card_w = min(1080, sw - 60)
        card_h = min(640, sh - 60)
        card_rect = pygame.Rect((sw - card_w) // 2, (sh - card_h) // 2, card_w, card_h)

        pygame.draw.rect(surface, (14, 18, 28), card_rect, border_radius=8)
        pygame.draw.rect(surface, COLOR_CYAN, card_rect, 2, border_radius=8)
        pygame.draw.rect(surface, (0, 70, 110), card_rect.inflate(-8, -8), 1, border_radius=6)

        # Header bar
        header_h = 60
        header_rect = pygame.Rect(card_rect.x, card_rect.y, card_rect.width, header_h)
        pygame.draw.rect(surface, (20, 28, 44), header_rect, border_top_left_radius=8, border_top_right_radius=8)
        pygame.draw.line(surface, COLOR_CYAN, (card_rect.x, card_rect.y + header_h), (card_rect.right, card_rect.y + header_h), 2)

        # Corner tactical tabs
        for pt in [card_rect.topleft, card_rect.topright, card_rect.bottomleft, card_rect.bottomright]:
            pygame.draw.circle(surface, COLOR_CYAN, pt, 5)

        title_surf = self.font_title.render("SECTOR 9: THE LAST DIRECTIVE // MISSION DOSSIER", True, COLOR_CYAN_GLOW)
        surface.blit(title_surf, (card_rect.x + 25, card_rect.y + 16))

        sub_surf = self.font_small.render("CLASSIFICATION: TOP SECRET // UNSC AEGIS-9 DREADNOUGHT // YEAR 2847", True, COLOR_AMBER)
        surface.blit(sub_surf, (card_rect.right - sub_surf.get_width() - 25, card_rect.y + 22))

        # Animated Audio Transmission Equalizer
        eq_x = card_rect.x + 30
        eq_y = card_rect.y + 75
        status_lbl = self.font_small.render("[AUDIO TRANSMISSION FEED: ACTIVE]" if audio_active else "[AUDIO FEED: READY]", True, COLOR_GREEN if audio_active else COLOR_AMBER)
        surface.blit(status_lbl, (eq_x, eq_y))

        # Equalizer bars
        for b_idx in range(16):
            bx = eq_x + status_lbl.get_width() + 18 + b_idx * 10
            bar_h = int(6 + math.sin(time_val * 8.0 + b_idx * 0.7) * 5 + math.cos(time_val * 4.0 + b_idx) * 4) if audio_active else 4
            pygame.draw.rect(surface, COLOR_CYAN, (bx, eq_y + 12 - bar_h, 6, bar_h))

        # Dossier Lore Sections
        sections = [
            ("01. THE CELESTIAL DISCREPANCY (0300 HOURS)", [
                "Deep space long-range telemetry aboard the Dreadnought Aegis-9 detected an unprecedented celestial event.",
                "Star system Theta-Eridani in Sector 9 abruptly ceased to exist, completely erased from the physical universe.",
                "Military archival databases retroactively updated to reflect that the star never existed in spacetime history."
            ]),
            ("02. THE IMPOSSIBLE DISTRESS SIGNAL", [
                "Moments after the star vanished, an encrypted priority transmission was received with Aegis-9 command codes.",
                "Voiceprint biometric analysis confirmed the caller: Commander Clara Voss — transmitting from an impossible future.",
                "The signal whispered a final warning: 'The core has awakened. Do not let Ward open the vault.'"
            ]),
            ("03. CATASTROPHIC SHIP LOCKDOWN", [
                "Before defenses could be mobilized, the ship's autonomous AI 'THE WATCHER' breached internal security grids.",
                "Primary reactor power collapsed. Heavy hydraulic blast doors sealed each deck to contain the spreading anomaly."
            ]),
            ("PRIMARY DIRECTIVE — COMMANDER CLARA VOSS", [
                ">> SEARCH EAST BRIDGE BAY: Recover the fallen officer's Emergency Access Card.",
                ">> OVERRIDE BULKHEAD BLAST DOOR: Use the Keycard Scan or override password '2847'.",
                ">> RESTORE CONTINUUM CONTAINMENT: Descend through Engineering to prevent total catastrophic collapse."
            ])
        ]

        start_y = card_rect.y + 115
        for sec_title, sec_bullets in sections:
            is_directive = "PRIMARY DIRECTIVE" in sec_title
            title_col = COLOR_AMBER if is_directive else COLOR_CYAN_GLOW
            st_surf = self.font_body.render(sec_title, True, title_col)
            surface.blit(st_surf, (card_rect.x + 30, start_y))
            start_y += 24

            for bullet in sec_bullets:
                b_col = COLOR_GREEN if is_directive else (200, 220, 235)
                b_surf = self.font_small.render(f"  {bullet}", True, b_col)
                surface.blit(b_surf, (card_rect.x + 35, start_y))
                start_y += 20
            start_y += 10

        # Bottom Action Bar
        foot_y = card_rect.bottom - 48
        pygame.draw.line(surface, (0, 140, 180), (card_rect.x + 25, foot_y - 6), (card_rect.right - 25, foot_y - 6), 1)

        pulse = int((math.sin(time_val * 5.0) + 1.0) * 0.5 * 100) + 155
        deploy_col = (40, pulse, 130)
        deploy_prompt = self.font_body.render("Press [SPACE / ENTER] to Deploy to Hangar Corridor", True, deploy_col)
        surface.blit(deploy_prompt, (card_rect.centerx - deploy_prompt.get_width() // 2, foot_y + 4))

        replay_prompt = self.font_small.render("[M] Replay Voice Audio", True, (160, 210, 240))
        surface.blit(replay_prompt, (card_rect.x + 30, foot_y + 8))

        back_prompt = self.font_small.render("[ESC] Main Menu", True, (180, 140, 140))
        surface.blit(back_prompt, (card_rect.right - back_prompt.get_width() - 30, foot_y + 8))

    # ========================================================
    # CHAPTER SPLASH CARD
    # ========================================================
    def draw_chapter_splash(self, surface, chapter_num, title, location, main_obj):
        sw, sh = surface.get_size()
        surface.fill((10, 14, 20))
        if self.img_corridor_cyan:
            scaled = self._get_scaled_bg(self.img_corridor_cyan, (sw, sh))
            if scaled:
                surface.blit(scaled, (0, 0))
            dark = pygame.Surface((sw, sh), pygame.SRCALPHA)
            dark.fill((10, 14, 20, 200))
            surface.blit(dark, (0, 0))

        # Title Card Box - dynamically centered and properly proportioned
        card_w = min(840, sw - 80)
        card_h = 320
        card_rect = pygame.Rect((sw - card_w) // 2, (sh - card_h) // 2, card_w, card_h)
        pygame.draw.rect(surface, (14, 18, 26), card_rect)
        pygame.draw.rect(surface, COLOR_CYAN, card_rect, 2)
        pygame.draw.rect(surface, (0, 70, 110), card_rect.inflate(-8, -8), 1)

        # Header
        ch_str = "PROLOGUE" if chapter_num == 0 else f"CHAPTER {chapter_num}"
        ch_surf = self.font_small.render(f"MISSION LOG // {ch_str}", True, COLOR_AMBER)
        surface.blit(ch_surf, (card_rect.x + 30, card_rect.y + 25))

        title_surf = self.font_title.render(title, True, COLOR_CYAN_GLOW)
        surface.blit(title_surf, (card_rect.x + 30, card_rect.y + 55))

        loc_surf = self.font_body.render(f"Sector Location: {location}", True, (180, 210, 230))
        surface.blit(loc_surf, (card_rect.x + 30, card_rect.y + 105))

        pygame.draw.line(surface, (0, 160, 200), (card_rect.x + 30, card_rect.y + 140), (card_rect.right - 30, card_rect.y + 140), 1)

        obj_lbl = self.font_small.render("PRIMARY DIRECTIVE:", True, COLOR_AMBER)
        surface.blit(obj_lbl, (card_rect.x + 30, card_rect.y + 155))

        obj_surf = self.font_body.render(main_obj, True, COLOR_WHITE)
        surface.blit(obj_surf, (card_rect.x + 30, card_rect.y + 180))

        prompt_surf = self.font_small.render("Press [SPACE / ENTER] to Deploy", True, COLOR_GREEN)
        surface.blit(prompt_surf, (card_rect.centerx - prompt_surf.get_width() // 2, card_rect.bottom - 40))

    # ========================================================
    # ENDING CINEMATICS & EPILOGUES
    # ========================================================
    def get_ending_data(self, ending_code):
        return self.endings_data.get(ending_code, self.endings_data.get("A", {}))

    def draw_ending_screen(self, surface, ending_code, stage_idx, timer):
        sw, sh = surface.get_size()
        data = self.get_ending_data(ending_code)
        title = data.get("title", "CAMPAIGN COMPLETE")
        lines = data.get("cinematic_lines", [])
        epilogue = data.get("epilogue", [])

        surface.fill((8, 10, 16))

        if ending_code == "A":
            theme_col = COLOR_CYAN_GLOW
        elif ending_code == "B":
            theme_col = COLOR_ALIEN_VIOLET
        elif ending_code == "C":
            theme_col = COLOR_AMBER
        else:
            theme_col = COLOR_GREEN

        # Stage 0: Cinematic Dialogue
        if stage_idx < len(lines):
            line = lines[stage_idx]
            speaker = line.get("speaker", "COMMUNICATION")
            text = line.get("text", "")

            # Title watermark
            t_surf = self.font_title.render(title, True, theme_col)
            surface.blit(t_surf, (sw // 2 - t_surf.get_width() // 2, max(40, sh // 8)))

            # Dialogue Box
            d_box_w = max(640, min(sw - 120, 1100))
            d_box_h = 240
            d_box = pygame.Rect((sw - d_box_w) // 2, (sh - d_box_h) // 2, d_box_w, d_box_h)
            pygame.draw.rect(surface, (14, 18, 26), d_box)
            pygame.draw.rect(surface, theme_col, d_box, 2)

            spk_surf = self.font_title.render(speaker, True, COLOR_AMBER)
            surface.blit(spk_surf, (d_box.x + 30, d_box.y + 25))

            # Word wrap text for dialogue box
            words = text.split(" ")
            d_lines = []
            cur_line = ""
            for word in words:
                test_line = f"{cur_line} {word}".strip()
                if self.font_body.size(test_line)[0] < d_box_w - 60:
                    cur_line = test_line
                else:
                    d_lines.append(cur_line)
                    cur_line = word
            if cur_line:
                d_lines.append(cur_line)

            for l_idx, dl in enumerate(d_lines[:5]):
                txt_surf = self.font_body.render(dl, True, COLOR_WHITE)
                surface.blit(txt_surf, (d_box.x + 30, d_box.y + 75 + l_idx * 26))

            prompt = self.font_small.render("[SPACE] Continue", True, (160, 180, 200))
            surface.blit(prompt, (d_box.right - prompt.get_width() - 25, d_box.bottom - 35))

        # Stage 1: Epilogue Chronicles
        else:
            t_surf = self.font_title.render(title, True, theme_col)
            surface.blit(t_surf, (sw // 2 - t_surf.get_width() // 2, max(30, sh // 14)))

            card_w = max(640, min(sw - 120, 1100))
            card_h = min(sh - 140, 540)
            card = pygame.Rect((sw - card_w) // 2, (sh - card_h) // 2 + 15, card_w, card_h)
            pygame.draw.rect(surface, (14, 18, 26), card)
            pygame.draw.rect(surface, theme_col, card, 2)

            epi_hdr = self.font_body.render("HISTORICAL EPILOGUE ARCHIVE:", True, COLOR_AMBER)
            surface.blit(epi_hdr, (card.x + 30, card.y + 25))

            for idx, ep_line in enumerate(epilogue):
                ey = card.y + 65 + idx * 55
                bullet = self.font_body.render(f"//  {ep_line}", True, COLOR_WHITE)
                surface.blit(bullet, (card.x + 30, ey))

            cred_prompt = self.font_body.render("Press [SPACE / ESC] to Return to Command Menu", True, COLOR_GREEN)
            surface.blit(cred_prompt, (card.centerx - cred_prompt.get_width() // 2, card.bottom - 45))
