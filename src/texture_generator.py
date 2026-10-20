import os
import pygame
import math
import random
from src.config import IMAGES_DIR

class TextureGenerator:
    _cached_textures = None

    @classmethod
    def get_textures(cls):
        if cls._cached_textures is None:
            cls._cached_textures = cls.generate_all()
        return cls._cached_textures

    @classmethod
    def _try_load_image(cls, filename, size=512):
        p = os.path.join(IMAGES_DIR, filename)
        if os.path.exists(p):
            try:
                img = pygame.image.load(p)
                if pygame.display.get_surface() is not None:
                    img = img.convert()
                if img.get_size() != (size, size):
                    img = pygame.transform.smoothscale(img, (size, size))
                return img
            except Exception as e:
                print(f"[TextureGenerator] Error loading image {filename}: {e}")
        return None

    @classmethod
    def generate_all(cls):
        size = 512
        textures = {}

        # -------------------------------------------------------------
        # 1. BLAST DOORS (Locked & Unlocked) - env_blast_door.png
        # -------------------------------------------------------------
        door_locked = cls._try_load_image("tex_door_locked.png", size)
        if door_locked is None:
            # Fallback directly to env_blast_door.png crop
            door_src = cls._try_load_image("env_blast_door.png", size)
            if door_src:
                door_locked = door_src
        
        door_unlocked = cls._try_load_image("tex_door_unlocked.png", size)

        # -------------------------------------------------------------
        # 2. HANGAR CORRIDOR WALL (Bridge / Main Hallway) - env_hangar_corridor.jpg
        # -------------------------------------------------------------
        wall_bridge = cls._try_load_image("tex_corridor_bridge.png", size)
        if wall_bridge is None:
            wall_bridge = cls._try_load_image("env_hangar_corridor.jpg", size)

        # -------------------------------------------------------------
        # 3. DEEP CONDUITS & CREW DECK - corridor_cyan.jpg
        # -------------------------------------------------------------
        wall_cyan = cls._try_load_image("tex_corridor_cyan.png", size)
        if wall_cyan is None:
            wall_cyan = cls._try_load_image("corridor_cyan.jpg", size)

        # -------------------------------------------------------------
        # 4. RESTRICTED LAB / CRYO BAY - env_lab_cryo.jpg
        # -------------------------------------------------------------
        wall_lab = cls._try_load_image("tex_lab.png", size)
        if wall_lab is None:
            wall_lab = cls._try_load_image("env_lab_cryo.jpg", size)

        # -------------------------------------------------------------
        # 5. HOLOGRAPHIC TERMINAL WALL - holo_terminal.jpg
        # -------------------------------------------------------------
        wall_term = cls._try_load_image("tex_terminal.png", size)
        if wall_term is None:
            wall_term = cls._try_load_image("holo_terminal.jpg", size)

        # Procedural fallback generator if image files were not found
        if wall_bridge is None:
            wall_bridge = cls._gen_proc_bridge(size)
        if door_locked is None:
            door_locked = cls._gen_proc_door(size, locked=True)
        if door_unlocked is None:
            door_unlocked = cls._gen_proc_door(size, locked=False)
        if wall_cyan is None:
            wall_cyan = wall_bridge
        if wall_lab is None:
            wall_lab = cls._gen_proc_lab(size)
        if wall_term is None:
            wall_term = cls._gen_proc_terminal(size)

        textures['bridge'] = wall_bridge
        textures['door_locked'] = door_locked
        textures['door_unlocked'] = door_unlocked
        textures['corridor'] = wall_cyan
        textures['crew'] = wall_cyan
        textures['engineering'] = wall_bridge
        textures['lab'] = wall_lab
        textures['vault'] = wall_lab
        textures['terminal'] = wall_term
        textures['comms'] = wall_term
        textures['observation'] = cls._gen_proc_observation(size)
        textures['distraction'] = cls._gen_proc_distraction(size)

        return textures

    @staticmethod
    def _gen_proc_bridge(size):
        surf = pygame.Surface((size, size))
        surf.fill((36, 44, 58))
        pygame.draw.rect(surf, (55, 68, 88), (0, 0, 48, size))
        pygame.draw.rect(surf, (55, 68, 88), (size - 48, 0, 48, size))
        pygame.draw.rect(surf, (22, 28, 40), (50, 30, size - 100, size - 60))
        pygame.draw.line(surf, (0, 220, 255), (60, 40), (size - 60, 40), 6)
        return surf

    @staticmethod
    def _gen_proc_door(size, locked=True):
        surf = pygame.Surface((size, size))
        surf.fill((40, 44, 52))
        color = (255, 45, 45) if locked else (40, 255, 130)
        pygame.draw.rect(surf, (24, 28, 36), (size // 4, size // 4, size // 2, size // 2))
        pygame.draw.circle(surf, color, (size // 2, size // 2), 32)
        return surf

    @staticmethod
    def _gen_proc_lab(size):
        surf = pygame.Surface((size, size))
        surf.fill((28, 22, 40))
        pygame.draw.line(surf, (0, 220, 255), (40, 0), (40, size), 8)
        pygame.draw.line(surf, (220, 60, 255), (size - 40, 0), (size - 40, size), 8)
        return surf

    @staticmethod
    def _gen_proc_terminal(size):
        surf = pygame.Surface((size, size))
        surf.fill((30, 36, 48))
        pygame.draw.rect(surf, (0, 60, 90), (30, 30, size - 60, size // 2))
        pygame.draw.rect(surf, (0, 220, 255), (30, 30, size - 60, size // 2), 3)
        return surf

    @staticmethod
    def _gen_proc_observation(size):
        surf = pygame.Surface((size, size))
        surf.fill((6, 6, 16))
        rnd = random.Random(42)
        for _ in range(120):
            x = rnd.randint(10, size - 10)
            y = rnd.randint(10, size - 10)
            c = rnd.randint(160, 255)
            surf.set_at((x, y), (c, c, 255))
        pygame.draw.rect(surf, (50, 60, 78), (0, 0, size, size), 24)
        return surf

    @staticmethod
    def _gen_proc_distraction(size):
        surf = pygame.Surface((size, size))
        surf.fill((45, 38, 25))
        pygame.draw.circle(surf, (255, 185, 20), (size // 2, size // 2), 48)
        pygame.draw.circle(surf, (255, 45, 45), (size // 2, size // 2), 16)
        return surf
