import pygame
import math
from src.config import (
    PLAYER_SPEED, PLAYER_RUN_SPEED, PLAYER_ROT_SPEED, PLAYER_RADIUS,
    MAX_HEALTH, MAX_FLASHLIGHT, FLASHLIGHT_DRAIN_RATE, FLASHLIGHT_RECHARGE_RATE,
    MOUSE_SENSITIVITY
)
from src.sound_system import SoundSystem

class Player:
    def __init__(self, x=1.5, y=1.5, angle=0.0):
        self.x = float(x)
        self.y = float(y)
        self.angle = float(angle)
        self.health = MAX_HEALTH
        self.max_health = MAX_HEALTH
        self.flashlight_on = True
        self.flashlight_battery = MAX_FLASHLIGHT
        self.max_flashlight = MAX_FLASHLIGHT

        self.inventory = []
        self.journal = []
        self.discovered_logs = set()
        self.checkpoint = (float(x), float(y), float(angle))

        # Smooth velocity and inertia
        self.vx = 0.0
        self.vy = 0.0
        self.acceleration = 18.0
        self.friction = 10.0
        self.head_bob = 0.0
        self.bob_timer = 0.0
        self.footstep_timer = 0.0
        self.sound = SoundSystem.get_instance()

    def set_checkpoint(self, x, y, angle):
        self.checkpoint = (float(x), float(y), float(angle))

    def respawn_at_checkpoint(self):
        self.x, self.y, self.angle = self.checkpoint
        self.vx = 0.0
        self.vy = 0.0
        self.health = max(50.0, self.health)

    def toggle_flashlight(self):
        if self.flashlight_battery > 5.0 or self.flashlight_on:
            self.flashlight_on = not self.flashlight_on
            self.sound.play('flashlight')

    def add_item(self, item_name):
        if item_name not in self.inventory:
            self.inventory.append(item_name)
            self.sound.play('access_granted')
            return True
        return False

    def has_item(self, item_name):
        return any(item_name.lower() in it.lower() for it in self.inventory)

    def add_log(self, log_key, log_title):
        if log_key not in self.discovered_logs:
            self.discovered_logs.add(log_key)
            self.journal.append(f"LOG: {log_title}")
            self.sound.play('ui_beep')
            return True
        return False

    def take_damage(self, amount):
        self.health = max(0.0, self.health - amount)
        self.sound.play('spark')
        return self.health <= 0.0

    def handle_input(self, keys, mouse_dx, dt, level_map):
        # Keyboard rotation (Smooth & responsive)
        if keys[pygame.K_LEFT]:
            self.angle -= PLAYER_ROT_SPEED * dt
        if keys[pygame.K_RIGHT]:
            self.angle += PLAYER_ROT_SPEED * dt

        # Smooth mouse rotation with delta clamping to prevent jerkiness
        if mouse_dx != 0:
            clamped_dx = max(-120.0, min(120.0, float(mouse_dx)))
            self.angle += clamped_dx * MOUSE_SENSITIVITY

        self.angle %= (2 * math.pi)

        # Target movement vector
        is_running = keys[pygame.K_LSHIFT] or keys[pygame.K_RSHIFT]
        max_speed = PLAYER_RUN_SPEED if is_running else PLAYER_SPEED

        cos_a = math.cos(self.angle)
        sin_a = math.sin(self.angle)
        target_dx = 0.0
        target_dy = 0.0

        if keys[pygame.K_w] or keys[pygame.K_UP]:
            target_dx += cos_a
            target_dy += sin_a
        if keys[pygame.K_s] or keys[pygame.K_DOWN]:
            target_dx -= cos_a
            target_dy -= sin_a
        if keys[pygame.K_a]:
            target_dx += sin_a
            target_dy -= cos_a
        if keys[pygame.K_d]:
            target_dx -= sin_a
            target_dy += cos_a

        t_len = math.hypot(target_dx, target_dy)
        if t_len > 0:
            target_dx = (target_dx / t_len) * max_speed
            target_dy = (target_dy / t_len) * max_speed

            # Head bobbing & footsteps
            self.bob_timer += dt * (12.0 if is_running else 8.0)
            self.head_bob = math.sin(self.bob_timer) * (3.5 if is_running else 2.0)

            self.footstep_timer += dt * (1.6 if is_running else 1.0)
            if self.footstep_timer >= 0.42:
                self.footstep_timer = 0.0
                self.sound.play('footstep', volume=0.35)
        else:
            self.head_bob *= 0.85

        # Smooth physics inertia & acceleration
        self.vx += (target_dx - self.vx) * min(1.0, self.acceleration * dt)
        self.vy += (target_dy - self.vy) * min(1.0, self.acceleration * dt)

        # Wall-sliding collision handling
        step_x = self.vx * dt
        step_y = self.vy * dt

        new_x = self.x + step_x
        new_y = self.y + step_y

        if not self._is_colliding(new_x, self.y, level_map):
            self.x = new_x
        else:
            self.vx = 0.0

        if not self._is_colliding(self.x, new_y, level_map):
            self.y = new_y
        else:
            self.vy = 0.0

        # Flashlight battery management
        if self.flashlight_on:
            self.flashlight_battery = max(0.0, self.flashlight_battery - FLASHLIGHT_DRAIN_RATE * dt)
            if self.flashlight_battery <= 0.0:
                self.flashlight_on = False
        else:
            self.flashlight_battery = min(MAX_FLASHLIGHT, self.flashlight_battery + FLASHLIGHT_RECHARGE_RATE * dt)

    def _is_colliding(self, test_x, test_y, level_map):
        r = PLAYER_RADIUS
        for ox in [-r, r]:
            for oy in [-r, r]:
                cx = int(test_x + ox)
                cy = int(test_y + oy)
                if 0 <= cy < len(level_map) and 0 <= cx < len(level_map[0]):
                    cell = level_map[cy][cx]
                    # Blocking cells ('O' is open door)
                    if cell in ['#', 'D', 'T', 'X', 'Z']:
                        return True
                else:
                    return True
        return False
