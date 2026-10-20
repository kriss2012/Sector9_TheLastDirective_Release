import pygame
import math
from src.config import FOV, HALF_FOV, MAX_DEPTH, COLOR_CYAN, COLOR_ALERT_RED, COLOR_AMBER
from src.texture_generator import TextureGenerator

class Raycaster:
    def __init__(self, render_width, render_height):
        self.render_width = render_width
        self.render_height = render_height
        self.num_rays = render_width
        self.delta_angle = FOV / self.num_rays
        self.textures = TextureGenerator.get_textures()
        self.z_buffer = [MAX_DEPTH] * self.num_rays

    def set_resolution(self, render_width, render_height):
        self.render_width = render_width
        self.render_height = render_height
        self.num_rays = render_width
        self.delta_angle = FOV / self.num_rays
        self.z_buffer = [MAX_DEPTH] * self.num_rays

    def render(self, surface, player, level_map, theme='bridge'):
        px, py = player.x, player.y
        pa = player.angle
        h = self.render_height
        w = self.render_width

        # Ceiling & Floor Theme Colors (Matching env_hangar_corridor.jpg and env_lab_cryo.jpg)
        if theme == 'lab':
            ceil_base = (26, 20, 38)
            floor_base = (20, 16, 30)
            neon_color = (195, 70, 255)
        elif theme == 'engineering':
            ceil_base = (32, 26, 22)
            floor_base = (26, 20, 16)
            neon_color = (255, 130, 40)
        elif theme == 'vault' or theme == 'engine':
            ceil_base = (18, 14, 28)
            floor_base = (14, 10, 22)
            neon_color = (180, 50, 255)
        else:
            # Bridge / Hangar (Image 1 style: deep steel blue with bright cyan/white ceiling beams)
            ceil_base = (30, 38, 52)
            floor_base = (24, 30, 40)
            neon_color = (0, 225, 255)

        surface.fill(ceil_base, (0, 0, w, h // 2))
        surface.fill(floor_base, (0, h // 2, w, h // 2))

        # Overhead central linear neon fixture in realistic 3D perspective (matching env_hangar_corridor.jpg)
        for ly in range(0, h // 2, 2):
            # Tapers down from foreground (top of screen) towards horizon vanishing point
            persp_factor = ((h // 2) - ly) / (h // 2)
            cur_w = max(4, int(w * 0.38 * persp_factor))
            cur_x = (w - cur_w) // 2

            glow_val = int(persp_factor * 75)
            line_col = (
                min(255, neon_color[0] // 3 + glow_val),
                min(255, neon_color[1] // 3 + glow_val),
                min(255, neon_color[2] // 3 + glow_val)
            )
            pygame.draw.line(surface, line_col, (cur_x, ly), (cur_x + cur_w, ly), 1)

            # Central bright white core
            core_w = max(2, int(cur_w * 0.35))
            pygame.draw.line(surface, (240, 255, 255), (w // 2 - core_w // 2, ly), (w // 2 + core_w // 2, ly), 1)

        # Floor Perspective Grating with metallic sheen and hazard margins (Image 1 style)
        for y_idx in range(h // 2, h, 3):
            persp_factor = (y_idx - (h // 2)) / (h // 2)
            metal_shade = int(22 + persp_factor * 56)
            pygame.draw.line(surface, (metal_shade, metal_shade + 4, metal_shade + 9), (0, y_idx), (w, y_idx), 1)

            # Dual yellow hazard perspective track converging towards horizon
            track_w = int(w * 0.65 * persp_factor)
            hazard_x1 = (w - track_w) // 2
            hazard_x2 = (w + track_w) // 2

            if (y_idx // 6) % 2 == 0:
                h_col = (min(255, int(210 * persp_factor)), min(255, int(155 * persp_factor)), 20)
                pygame.draw.line(surface, h_col, (hazard_x1 - 4, y_idx), (hazard_x1 + 4, y_idx), 2)
                pygame.draw.line(surface, h_col, (hazard_x2 - 4, y_idx), (hazard_x2 + 4, y_idx), 2)

        # DDA Raycasting Loop
        start_angle = pa - HALF_FOV
        default_wall_tex = self.textures.get(theme, self.textures['bridge'])

        for ray in range(self.num_rays):
            ray_angle = start_angle + ray * self.delta_angle
            sin_a = math.sin(ray_angle) if abs(math.sin(ray_angle)) > 1e-6 else 1e-6
            cos_a = math.cos(ray_angle) if abs(math.cos(ray_angle)) > 1e-6 else 1e-6

            x_map = int(px)
            y_map = int(py)

            delta_dist_x = abs(1.0 / cos_a)
            delta_dist_y = abs(1.0 / sin_a)

            if cos_a < 0:
                step_x = -1
                side_dist_x = (px - x_map) * delta_dist_x
            else:
                step_x = 1
                side_dist_x = (x_map + 1.0 - px) * delta_dist_x

            if sin_a < 0:
                step_y = -1
                side_dist_y = (py - y_map) * delta_dist_y
            else:
                step_y = 1
                side_dist_y = (y_map + 1.0 - py) * delta_dist_y

            hit = False
            side = 0
            hit_cell = '#'

            while not hit:
                if side_dist_x < side_dist_y:
                    side_dist_x += delta_dist_x
                    x_map += step_x
                    side = 0
                else:
                    side_dist_y += delta_dist_y
                    y_map += step_y
                    side = 1

                if 0 <= y_map < len(level_map) and 0 <= x_map < len(level_map[0]):
                    cell = level_map[y_map][x_map]
                    if cell in ['#', 'D', 'O', 'T', 'X', 'P', 'Z']:
                        hit = True
                        hit_cell = cell
                else:
                    break

            if not hit:
                self.z_buffer[ray] = MAX_DEPTH
                continue

            if side == 0:
                perp_wall_dist = (x_map - px + (1 - step_x) / 2.0) / cos_a
            else:
                perp_wall_dist = (y_map - py + (1 - step_y) / 2.0) / sin_a

            perp_wall_dist = max(0.08, perp_wall_dist)
            self.z_buffer[ray] = perp_wall_dist

            line_height = int(h / perp_wall_dist)
            draw_start = max(0, -line_height // 2 + h // 2)
            draw_end = min(h, line_height // 2 + h // 2)

            if hit_cell == 'D':
                texture = self.textures['door_locked']
            elif hit_cell == 'O':
                texture = self.textures['door_unlocked']
            elif hit_cell == 'T':
                texture = self.textures['terminal']
            elif hit_cell == 'X':
                texture = self.textures['distraction']
            elif hit_cell == 'Z':
                texture = self.textures['observation']
            else:
                texture = default_wall_tex

            tex_w = texture.get_width()
            tex_h = texture.get_height()

            if side == 0:
                wall_x = py + perp_wall_dist * sin_a
            else:
                wall_x = px + perp_wall_dist * cos_a
            wall_x -= math.floor(wall_x)

            tex_x = int(wall_x * tex_w)
            if (side == 0 and cos_a > 0) or (side == 1 and sin_a < 0):
                tex_x = tex_w - tex_x - 1

            tex_x = max(0, min(tex_w - 1, tex_x))

            # Sample vertical texture slice
            col_slice = texture.subsurface((tex_x, 0, 1, tex_h))
            scaled_slice = pygame.transform.scale(col_slice, (1, draw_end - draw_start))

            # Balanced Ambient Sci-Fi Lighting:
            # Guarantees sharp, vibrant visibility of textures and details
            dist_factor = min(1.0, perp_wall_dist / MAX_DEPTH)
            min_ambient = 0.62  # Ample ambient light so corridors are clearly visible
            brightness = min_ambient + (1.0 - min_ambient) * (1.0 - dist_factor)

            # Subtle side shading for 3D realism
            side_mult = 0.88 if side == 1 else 1.0
            brightness *= side_mult

            # Flashlight searchlight cone
            if player.flashlight_on:
                center_offset = abs(ray - self.num_rays // 2) / (self.num_rays // 2)
                if center_offset < 0.75:
                    boost = (1.0 - center_offset / 0.75) * max(0.0, 1.0 - dist_factor * 0.6) * 0.55
                    brightness = min(1.35, brightness + boost)

            # Fast in-place lighting tint (no surface allocations)
            r_tint = int(min(255, 255 * brightness))
            g_tint = int(min(255, 255 * brightness * (0.96 + 0.04 * (1.0 - dist_factor))))
            b_tint = int(min(255, 255 * brightness * (1.0 + 0.08 * (1.0 - dist_factor))))
            scaled_slice.fill((r_tint, g_tint, b_tint), special_flags=pygame.BLEND_MULT)

            surface.blit(scaled_slice, (ray, draw_start))

        return self.z_buffer

    def draw_minimap(self, surface, player, level_map, origin=(16, 16), scale=7):
        ox, oy = origin
        px, py = player.x, player.y

        mw = len(level_map[0]) * scale
        mh = len(level_map) * scale
        bg_rect = pygame.Rect(ox - 3, oy - 3, mw + 6, mh + 6)
        pygame.draw.rect(surface, (12, 16, 24), bg_rect)
        pygame.draw.rect(surface, COLOR_CYAN, bg_rect, 1)

        for r, row in enumerate(level_map):
            for c, char in enumerate(row):
                rect = pygame.Rect(ox + c * scale, oy + r * scale, scale, scale)
                if char == '#':
                    pygame.draw.rect(surface, (45, 52, 68), rect)
                elif char in ['D', 'O']:
                    pygame.draw.rect(surface, (255, 45, 45) if char == 'D' else (40, 255, 130), rect)
                elif char == 'T':
                    pygame.draw.rect(surface, (0, 220, 255), rect)
                elif char == 'X':
                    pygame.draw.rect(surface, (255, 185, 20), rect)

        center_x = int(ox + px * scale)
        center_y = int(oy + py * scale)
        pygame.draw.circle(surface, (0, 255, 130), (center_x, center_y), 4)
        end_x = int(center_x + math.cos(player.angle) * 9)
        end_y = int(center_y + math.sin(player.angle) * 9)
        pygame.draw.line(surface, (0, 230, 255), (center_x, center_y), (end_x, end_y), 2)
