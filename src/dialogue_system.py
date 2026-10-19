import json
import os
import math
import pygame
from src.config import DATA_DIR, COLOR_CYAN, COLOR_WHITE, COLOR_AMBER
from src.sound_system import SoundSystem

class DialogueManager:
    def __init__(self):
        self.dialogues_data = {}
        self.load_data()
        self.active_sequence = []
        self.current_line_idx = 0
        self.displayed_chars = 0
        self.char_timer = 0.0
        self.char_speed = 0.025  # seconds per character
        self.on_complete_callback = None
        self.is_active = False
        self.sound = SoundSystem.get_instance()

        self.font_speaker = pygame.font.SysFont("arial", 20, bold=True)
        self.font_text = pygame.font.SysFont("arial", 18)
        self.font_prompt = pygame.font.SysFont("arial", 14)

    def load_data(self):
        path = os.path.join(DATA_DIR, "dialogues.json")
        if os.path.exists(path):
            with open(path, 'r', encoding='utf-8') as f:
                self.dialogues_data = json.load(f)

    def start_sequence(self, sequence, on_complete=None):
        if not sequence:
            if on_complete: on_complete()
            return
        self.active_sequence = sequence
        self.current_line_idx = 0
        self.displayed_chars = 0
        self.char_timer = 0.0
        self.on_complete_callback = on_complete
        self.is_active = True
        self._play_line_sound()

    def start_dialogue_by_id(self, chapter_key, dialogue_key, on_complete=None):
        ch = self.dialogues_data.get(chapter_key, {})
        seq = ch.get(dialogue_key, [])
        self.start_sequence(seq, on_complete)

    def _play_line_sound(self):
        if self.current_line_idx < len(self.active_sequence):
            line = self.active_sequence[self.current_line_idx]
            speaker = line.get("speaker", "UNKNOWN")
            self.sound.play('radio_burst', volume=0.25)
            self.sound.play_voice(speaker)

    def update(self, dt):
        if not self.is_active or not self.active_sequence:
            return

        line = self.active_sequence[self.current_line_idx]
        full_text = line.get("text", "")

        if self.displayed_chars < len(full_text):
            self.char_timer += dt
            if self.char_timer >= self.char_speed:
                self.char_timer = 0.0
                self.displayed_chars += 1
                if self.displayed_chars % 3 == 0:
                    self.sound.play_voice(line.get("speaker", "default"))

    def advance(self):
        if not self.is_active:
            return

        line = self.active_sequence[self.current_line_idx]
        full_text = line.get("text", "")

        # If line not fully displayed, reveal all immediately
        if self.displayed_chars < len(full_text):
            self.displayed_chars = len(full_text)
            self.sound.play('ui_beep')
            return

        # Advance to next line
        self.current_line_idx += 1
        if self.current_line_idx >= len(self.active_sequence):
            self.is_active = False
            self.active_sequence = []
            if self.on_complete_callback:
                cb = self.on_complete_callback
                self.on_complete_callback = None
                cb()
        else:
            self.displayed_chars = 0
            self.char_timer = 0.0
            self._play_line_sound()

    def handle_input(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key in [pygame.K_SPACE, pygame.K_RETURN, pygame.K_e]:
                self.advance()
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            self.advance()

    def draw(self, surface):
        if not self.is_active or not self.active_sequence:
            return

        line = self.active_sequence[self.current_line_idx]
        speaker = line.get("speaker", "COMMUNICATION")
        full_text = line.get("text", "")
        text_color = tuple(line.get("color", [0, 225, 255]))
        visible_text = full_text[:self.displayed_chars]

        # Calculate responsive full-screen layout
        sw, sh = surface.get_size()
        box_w = min(1200, max(760, sw - 120))
        box_h = 145
        box_x = (sw - box_w) // 2
        box_y = sh - box_h - 22

        # Translucent glassmorphism background
        box_surf = pygame.Surface((box_w, box_h), pygame.SRCALPHA)
        box_surf.fill((10, 14, 22, 238))
        surface.blit(box_surf, (box_x, box_y))

        # Glowing border & tactical accent corners
        pygame.draw.rect(surface, (0, 180, 240), (box_x, box_y, box_w, box_h), 2)
        pygame.draw.rect(surface, (0, 60, 95), (box_x + 3, box_y + 3, box_w - 6, box_h - 6), 1)
        for corner in [(box_x, box_y), (box_x + box_w, box_y), (box_x, box_y + box_h), (box_x + box_w, box_y + box_h)]:
            pygame.draw.circle(surface, COLOR_CYAN, corner, 4)

        # Speaker tab header badge
        spk_surf = self.font_speaker.render(speaker, True, text_color)
        spk_w = spk_surf.get_width() + 28
        spk_rect = pygame.Rect(box_x + 24, box_y - 16, spk_w, 28)
        pygame.draw.rect(surface, (18, 28, 44), spk_rect)
        pygame.draw.rect(surface, (0, 210, 255), spk_rect, 1)
        surface.blit(spk_surf, (spk_rect.x + 14, spk_rect.y + 3))

        # Sci-Fi Comms Audio Waveform Visualizer Badge (left side)
        badge_w, badge_h = 74, 88
        badge_x = box_x + 20
        badge_y = box_y + 26
        badge_rect = pygame.Rect(badge_x, badge_y, badge_w, badge_h)
        pygame.draw.rect(surface, (14, 20, 32), badge_rect)
        pygame.draw.rect(surface, (0, 140, 200), badge_rect, 1)

        # Draw animated audio waveform bars
        t = pygame.time.get_ticks() / 1000.0
        bar_count = 6
        bar_w = 6
        spacing = 4
        start_bx = badge_x + 10
        for b_i in range(bar_count):
            h_val = int(12 + 18 * abs(math.sin(t * 5.0 + b_i * 1.1)))
            bx = start_bx + b_i * (bar_w + spacing)
            by = badge_y + (badge_h // 2) - (h_val // 2)
            b_col = COLOR_CYAN if (b_i % 2 == 0) else COLOR_AMBER
            pygame.draw.rect(surface, b_col, (bx, by, bar_w, h_val))

        badge_lbl = self.font_prompt.render("COMM-LINK", True, (130, 180, 210))
        surface.blit(badge_lbl, (badge_x + (badge_w - badge_lbl.get_width()) // 2, badge_y + badge_h - 18))

        # Word wrap dialogue text across box (offset right of the badge)
        text_start_x = badge_x + badge_w + 24
        max_text_w = box_w - (badge_w + 64)
        words = visible_text.split(" ")
        lines = []
        cur_line = ""
        for word in words:
            test_line = f"{cur_line} {word}".strip()
            if self.font_text.size(test_line)[0] < max_text_w:
                cur_line = test_line
            else:
                lines.append(cur_line)
                cur_line = word
        if cur_line:
            lines.append(cur_line)

        for idx, l in enumerate(lines[:3]):
            rendered_line = self.font_text.render(l, True, COLOR_WHITE)
            surface.blit(rendered_line, (text_start_x, box_y + 28 + idx * 26))

        # Prompt hint in bottom-right corner
        prompt_surf = self.font_prompt.render("[SPACE / E / CLICK] Continue", True, COLOR_AMBER)
        surface.blit(prompt_surf, (box_x + box_w - prompt_surf.get_width() - 24, box_y + box_h - 24))
