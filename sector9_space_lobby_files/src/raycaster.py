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

    def render(self, surface, player, level_map, theme='bridge', doors=None, wall_tex_map=None):
        # doors:        optional {(x, y): Door} - per-door texture + sliding animation
        # wall_tex_map: optional {(x, y): texture_name} - per-cell wall style (lobby zones)
        px, py = player.x, player.y
        pa = player.angle
        h = self.render_height
        w = self.render_width

        # Ceiling & Floor Theme Lighting (Matching Reference Images 1 & 2)
        if theme == 'lab':
            ceil_base = (20, 16, 32)
            floor_base = (16, 14, 24)
            neon_color = (195, 70, 255)
        elif theme == 'engineering':
            ceil_base = (24, 20, 18)
            floor_base = (20, 18, 16)
            neon_color = (255, 120, 40)
        elif theme == 'lobby':
            # Space lobby: bright, clean station lighting (concept images 1-3)
            ceil_base = (58, 62, 72)
            floor_base = (34, 36, 42)
            neon_color = (255, 236, 190)
        elif theme == 'vault' or theme == 'engine':
            ceil_base = (14, 10, 22)
            floor_base = (12, 8, 18)
            neon_color = (180, 50, 255)
        else:
            # Bridge / Hangar (Image 1 style: cool titanium blue with cyan neon)
            ceil_base = (22, 28, 40)
            floor_base = (18, 22, 30)
            neon_color = (0, 220, 255)

        surface.fill(ceil_base, (0, 0, w, h // 2))
        surface.fill(floor_base, (0, h // 2, w, h // 2))

        # Overhead central linear neon fixture (matching Image 1)
        overhead_w = int(w * 0.18)
        overhead_x = (w - overhead_w) // 2
        for ly in range(0, h // 2, 4):
            intensity = int(max(0, 1.0 - (ly / (h // 2))) * 45)
            line_col = (
                min(255, neon_color[0] // 3 + intensity),
                min(255, neon_color[1] // 3 + intensity),
                min(255, neon_color[2] // 3 + intensity)
            )
            pygame.draw.line(surface, line_col, (overhead_x, ly), (overhead_x + overhead_w, ly), 1)

        # Floor Perspective Grate Lines with yellow hazard border
        for y_idx in range(h // 2, h, 6):
            depth_factor = (y_idx - h // 2) / (h // 2)
            shade = int(20 + depth_factor * 35)
            pygame.draw.line(surface, (shade, shade + 2, shade + 6), (0, y_idx), (w, y_idx))

        # DDA Raycasting Loop
        start_angle = pa - HALF_FOV
        tex_size = 256
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

            door = doors.get((x_map, y_map)) if (doors and hit_cell == 'D') else None
            if door is not None:
                texture = self.textures.get(door.texture_key, self.textures['door_locked'])
            elif hit_cell == 'D':
                texture = self.textures['door_locked']
            elif hit_cell == 'O':
                texture = self.textures['door_unlocked']
            elif hit_cell == 'T':
                texture = self.textures['terminal']
            elif hit_cell == 'X':
                texture = self.textures['distraction']
            elif hit_cell == 'Z':
                texture = self.textures['observation']
            elif wall_tex_map is not None and (x_map, y_map) in wall_tex_map:
                texture = self.textures.get(wall_tex_map[(x_map, y_map)], default_wall_tex)
            else:
                texture = default_wall_tex

            if side == 0:
                wall_x = py + perp_wall_dist * sin_a
            else:
                wall_x = px + perp_wall_dist * cos_a
            wall_x -= math.floor(wall_x)

            tex_x = int(wall_x * tex_size)
            flip = (side == 0 and cos_a > 0) or (side == 1 and sin_a < 0)
            if theme == 'lobby':
                # The original flip rule mirrors every wall face (harmless for the old
                # symmetric textures). Lobby textures carry text, so draw them un-mirrored.
                flip = not flip
            if flip:
                tex_x = tex_size - tex_x - 1

            tex_x = max(0, min(tex_size - 1, tex_x))

            dist_factor = min(1.0, perp_wall_dist / MAX_DEPTH)
            shade = 0.75 if side == 1 else 1.0

            if player.flashlight_on:
                center_offset = abs(ray - self.num_rays // 2) / (self.num_rays // 2)
                flashlight_boost = max(0.0, (1.0 - center_offset * 1.4) * (1.0 - dist_factor * 0.6) * 0.7)
                shade = min(1.3, shade + flashlight_boost)

            col_slice = texture.subsurface((tex_x, 0, 1, tex_size))
            scaled_slice = pygame.transform.scale(col_slice, (1, draw_end - draw_start))

            final_alpha = int(max(0, min(255, (1.0 - (shade * (1.0 - dist_factor))) * 255)))
            if final_alpha > 0:
                dark_surf = pygame.Surface((1, draw_end - draw_start))
                dark_surf.fill((0, 0, 0))
                dark_surf.set_alpha(final_alpha)
                scaled_slice.blit(dark_surf, (0, 0))

            if door is not None and door.progress > 0.0:
                # Shutter door: the leaf slides up into the ceiling as it opens.
                col_h = draw_end - draw_start
                shift = min(col_h - 1, int(col_h * door.progress))
                if col_h - shift > 0:
                    surface.blit(scaled_slice, (ray, draw_start), pygame.Rect(0, shift, 1, col_h - shift))
            else:
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
