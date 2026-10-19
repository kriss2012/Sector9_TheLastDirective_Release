import pygame
import math
import random

class SpriteObject:
    def __init__(self, x, y, sprite_type, entity_id=None, interactive=False, label="", is_objective=False):
        self.x = float(x)
        self.y = float(y)
        self.sprite_type = sprite_type
        self.entity_id = entity_id or f"{sprite_type}_{int(x)}_{int(y)}"
        self.interactive = interactive
        self.label = label
        self.is_objective = is_objective
        self.active = True
        self.anim_time = 0.0

    def update(self, dt):
        self.anim_time += dt

class SpriteRenderer:
    def __init__(self):
        self.sprites_cache = {}
        self.font_waypoint = pygame.font.SysFont("arial", 12, bold=True)
        self._init_sprites()

    def _init_sprites(self):
        size = 128

        # 1. Access Keycard / Beacon Item with vertical light column
        s = pygame.Surface((size, size), pygame.SRCALPHA)
        # Vertical cyan/gold light pillar
        for w_step in range(12, 0, -2):
            alpha = int(40 - w_step * 2.5)
            pygame.draw.rect(s, (0, 220, 255, alpha), (size // 2 - w_step, 0, w_step * 2, size - 20))
        # Floating access keycard
        card_rect = pygame.Rect(size // 2 - 24, size - 50, 48, 30)
        pygame.draw.rect(s, (0, 190, 255), card_rect, border_radius=4)
        pygame.draw.rect(s, (255, 255, 255), (card_rect.x + 6, card_rect.y + 6, 16, 18), border_radius=2)
        pygame.draw.circle(s, (255, 200, 50), (card_rect.right - 14, card_rect.centery), 6)
        self.sprites_cache['keycard'] = s
        self.sprites_cache['chip'] = s

        # 2. Fallen Crew Member (with glowing emergency beacon on suit)
        s = pygame.Surface((size, size), pygame.SRCALPHA)
        # Body silhouette
        pygame.draw.ellipse(s, (38, 48, 68), (20, size - 55, 88, 38))
        pygame.draw.circle(s, (210, 185, 160), (32, size - 42), 14)
        pygame.draw.rect(s, (22, 28, 40), (55, size - 45, 45, 20), border_radius=4)
        # Pulsing emergency locator beacon on officer's shoulder
        pygame.draw.circle(s, (255, 175, 20, 180), (60, size - 48), 12)
        pygame.draw.circle(s, (255, 255, 200), (60, size - 48), 5)
        self.sprites_cache['fallen_crew'] = s

        # 3. Cryo Storage Capsule (Matching User Reference Image 2)
        s = pygame.Surface((size, size), pygame.SRCALPHA)
        # Steel base and cap
        pygame.draw.rect(s, (45, 52, 65), (size // 2 - 28, size - 24, 56, 22), border_radius=3)
        pygame.draw.rect(s, (45, 52, 65), (size // 2 - 28, 8, 56, 18), border_radius=3)
        # Cylindrical glass tube
        tube_rect = pygame.Rect(size // 2 - 22, 24, 44, size - 48)
        pygame.draw.rect(s, (0, 70, 110, 160), tube_rect, border_radius=8)
        pygame.draw.rect(s, (0, 220, 255), tube_rect, 2, border_radius=8)
        # Glowing inner cryo liquid
        pygame.draw.rect(s, (0, 200, 255, 190), (size // 2 - 18, 32, 36, size - 64), border_radius=6)
        pygame.draw.rect(s, (220, 255, 255, 220), (size // 2 - 14, 38, 10, size - 76))
        self.sprites_cache['cryo_capsule'] = s

        # 4. Maintenance Tool
        s = pygame.Surface((size, size), pygame.SRCALPHA)
        pygame.draw.rect(s, (190, 140, 35), (size // 2 - 8, 25, 16, 75), border_radius=4)
        pygame.draw.circle(s, (230, 230, 240), (size // 2, 28), 22, 8)
        pygame.draw.rect(s, (35, 40, 50), (size // 2 - 12, 70, 24, 30), border_radius=2)
        self.sprites_cache['tool'] = s

        # 5. Science Director's Badge
        s = pygame.Surface((size, size), pygame.SRCALPHA)
        pygame.draw.polygon(s, (0, 235, 255), [(size // 2, 20), (size // 2 + 35, 50), (size // 2 + 20, 95), (size // 2 - 20, 95), (size // 2 - 35, 50)])
        pygame.draw.polygon(s, (255, 255, 255), [(size // 2, 32), (size // 2 + 22, 54), (size // 2 + 12, 84), (size // 2 - 12, 84), (size // 2 - 22, 54)])
        self.sprites_cache['badge'] = s

        # 6. Hazard Filter Canister
        s = pygame.Surface((size, size), pygame.SRCALPHA)
        pygame.draw.rect(s, (255, 165, 20), (size // 2 - 25, 30, 50, 70), border_radius=8)
        pygame.draw.rect(s, (35, 38, 45), (size // 2 - 28, 22, 56, 12), border_radius=3)
        pygame.draw.rect(s, (35, 38, 45), (size // 2 - 28, 96, 56, 12), border_radius=3)
        pygame.draw.circle(s, (18, 20, 25), (size // 2, 65), 10)
        self.sprites_cache['filter'] = s

        # 7. Watcher Sentry Drone
        s = pygame.Surface((size, size), pygame.SRCALPHA)
        pts = [(size // 2, 18), (size // 2 + 38, 38), (size // 2 + 45, 75), (size // 2 + 25, 100), (size // 2 - 25, 100), (size // 2 - 45, 75), (size // 2 - 38, 38)]
        pygame.draw.polygon(s, (32, 28, 42), pts)
        pygame.draw.polygon(s, (85, 75, 105), pts, 3)
        # Red surveillance eye
        pygame.draw.circle(s, (255, 30, 30), (size // 2, 65), 20)
        pygame.draw.circle(s, (255, 220, 220), (size // 2, 65), 7)
        self.sprites_cache['drone'] = s

        # 8. Dr. Sera Nahl's Hologram
        s = pygame.Surface((size, size), pygame.SRCALPHA)
        pygame.draw.circle(s, (100, 255, 220, 180), (size // 2, 30), 16)
        pygame.draw.polygon(s, (100, 255, 220, 150), [(size // 2 - 22, 50), (size // 2 + 22, 50), (size // 2 + 30, 115), (size // 2 - 30, 115)])
        for y in range(30, 115, 6):
            pygame.draw.line(s, (200, 255, 245, 210), (size // 2 - 32, y), (size // 2 + 32, y), 1)
        self.sprites_cache['sera_hologram'] = s

        # 9. The Watcher Silhouette
        s = pygame.Surface((size, size), pygame.SRCALPHA)
        pygame.draw.polygon(s, (18, 12, 28, 230), [(size // 2, 15), (size // 2 + 28, 48), (size // 2 + 32, 118), (size // 2 - 32, 118), (size // 2 - 28, 48)])
        pygame.draw.polygon(s, (195, 70, 255, 200), [(size // 2, 15), (size // 2 + 28, 48), (size // 2 + 32, 118), (size // 2 - 32, 118), (size // 2 - 28, 48)], 3)
        pygame.draw.circle(s, (255, 255, 255), (size // 2, 48), 6)
        self.sprites_cache['watcher_silhouette'] = s

        # 10. Memory Projection Pedestal
        s = pygame.Surface((size, size), pygame.SRCALPHA)
        pygame.draw.polygon(s, (45, 52, 68), [(size // 2 - 25, 115), (size // 2 + 25, 115), (size // 2 + 18, 80), (size // 2 - 18, 80)])
        pygame.draw.circle(s, (255, 210, 80, 200), (size // 2, 50), 24)
        pygame.draw.circle(s, (255, 255, 255, 240), (size // 2, 50), 8)
        self.sprites_cache['projection'] = s

    def render_sprites(self, surface, sprites, player, z_buffer, render_width, render_height, fov, half_fov):
        px, py, pa = player.x, player.y, player.angle

        sorted_sprites = []
        for sp in sprites:
            if not sp.active: continue
            dx = sp.x - px
            dy = sp.y - py
            dist = math.hypot(dx, dy)
            if dist < 0.15 or dist > 22.0: continue

            sprite_angle = math.atan2(dy, dx) - pa
            while sprite_angle > math.pi: sprite_angle -= 2 * math.pi
            while sprite_angle < -math.pi: sprite_angle += 2 * math.pi

            if -half_fov - 0.25 < sprite_angle < half_fov + 0.25:
                sorted_sprites.append((dist, sprite_angle, sp))

        sorted_sprites.sort(key=lambda item: item[0], reverse=True)

        for dist, spr_angle, sp in sorted_sprites:
            dist_correct = dist * math.cos(spr_angle)
            if dist_correct <= 0.08: continue

            screen_x = int((spr_angle / fov + 0.5) * render_width)
            sprite_h = int(render_height / dist_correct)
            sprite_w = sprite_h

            if sprite_h <= 3: continue

            # Hover bobbing
            y_offset = 0
            if sp.sprite_type in ['drone', 'sera_hologram', 'projection', 'keycard', 'chip']:
                y_offset = int(math.sin(sp.anim_time * 3.2) * (sprite_h * 0.09))

            top_y = (render_height - sprite_h) // 2 + y_offset

            raw_tex = self.sprites_cache.get(sp.sprite_type, self.sprites_cache['chip'])
            scaled_tex = pygame.transform.scale(raw_tex, (sprite_w, sprite_h))

            # Lighting / fog
            shade_factor = max(0.25, min(1.0, 1.0 - (dist / 20.0)))
            if shade_factor < 0.99:
                dark_surf = pygame.Surface((sprite_w, sprite_h), pygame.SRCALPHA)
                dark_alpha = int((1.0 - shade_factor) * 190)
                dark_surf.fill((0, 0, 0, dark_alpha))
                scaled_tex.blit(dark_surf, (0, 0), special_flags=pygame.BLEND_RGBA_SUB)

            start_x = screen_x - sprite_w // 2
            for col in range(sprite_w):
                cur_x = start_x + col
                if 0 <= cur_x < render_width:
                    if dist_correct < z_buffer[cur_x]:
                        col_slice = scaled_tex.subsurface((col, 0, 1, sprite_h))
                        surface.blit(col_slice, (cur_x, top_y))

            # If sprite is an objective or item, draw floating 3D waypoint beacon!
            if (sp.is_objective or sp.interactive) and dist_correct < 16.0:
                wp_y = max(10, top_y - 20)
                if 0 <= screen_x < render_width and dist_correct < z_buffer[screen_x]:
                    # Pulsing beacon ring
                    ring_r = int(6 + math.sin(sp.anim_time * 4.0) * 3)
                    pygame.draw.circle(surface, (0, 230, 255), (screen_x, wp_y), ring_r, 1)
                    pygame.draw.circle(surface, (255, 200, 50), (screen_x, wp_y), 3)

                    # Distance text
                    d_txt = f"{dist:.1f}m"
                    lbl_surf = self.font_waypoint.render(d_txt, True, (255, 220, 80))
                    surface.blit(lbl_surf, (screen_x - lbl_surf.get_width() // 2, wp_y - 14))
