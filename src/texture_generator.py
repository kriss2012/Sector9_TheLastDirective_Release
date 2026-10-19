import pygame
import math
import random

class TextureGenerator:
    _cached_textures = None

    @classmethod
    def get_textures(cls):
        if cls._cached_textures is None:
            cls._cached_textures = cls.generate_all()
        return cls._cached_textures

    @classmethod
    def generate_all(cls):
        size = 256
        textures = {}

        # -------------------------------------------------------------
        # 1. BRIDGE / HANGAR CORRIDOR (Matching User Concept Image 1)
        # Structural steel pillars, overhead neon fixtures, hazard stripes
        # -------------------------------------------------------------
        surf = pygame.Surface((size, size))
        surf.fill((28, 34, 46))  # Deep steel blue base

        # Structural vertical pillar frames
        pygame.draw.rect(surf, (45, 54, 72), (0, 0, 36, size))
        pygame.draw.rect(surf, (45, 54, 72), (size - 36, 0, 36, size))
        pygame.draw.line(surf, (70, 85, 115), (36, 0), (36, size), 2)
        pygame.draw.line(surf, (70, 85, 115), (size - 36, 0), (size - 36, size), 2)

        # Central recessed panel
        pygame.draw.rect(surf, (18, 22, 32), (38, 20, size - 76, size - 40))
        pygame.draw.rect(surf, (35, 42, 58), (38, 20, size - 76, size - 40), 2)

        # Overhead bright linear neon lighting fixture (Image 1 style)
        pygame.draw.rect(surf, (15, 20, 30), (45, 16, size - 90, 18))
        pygame.draw.rect(surf, (0, 220, 255), (55, 20, size - 110, 10))
        pygame.draw.rect(surf, (240, 255, 255), (60, 22, size - 120, 6))

        # Horizontal ventilation grill slats
        for gy in range(60, 130, 12):
            pygame.draw.rect(surf, (12, 14, 20), (50, gy, size - 100, 7))
            pygame.draw.line(surf, (55, 65, 85), (52, gy + 1), (size - 52, gy + 1), 1)

        # Holographic telemetry display
        pygame.draw.rect(surf, (0, 45, 70), (56, 145, size - 112, 45))
        pygame.draw.rect(surf, (0, 200, 255), (56, 145, size - 112, 45), 2)
        for tx in range(64, size - 64, 18):
            pygame.draw.line(surf, (0, 240, 255), (tx, 152), (tx, 182), 2)
        pygame.draw.line(surf, (255, 255, 255), (62, 168), (size - 62, 168), 1)

        # Yellow-black industrial hazard warning stripes on floor margin (Image 1 style)
        for h in range(0, size, 32):
            pygame.draw.polygon(surf, (255, 175, 20), [(h, size - 24), (h + 16, size - 24), (h + 32, size), (h + 16, size)])
            pygame.draw.polygon(surf, (20, 22, 28), [(h + 16, size - 24), (h + 32, size - 24), (h + 48, size), (h + 32, size)])
        pygame.draw.line(surf, (255, 200, 50), (0, size - 24), (size, size - 24), 2)
        textures['bridge'] = surf

        # -------------------------------------------------------------
        # 2. ENGINEERING DECK (Heavy industrial iron, copper coolant pipes, vents)
        # -------------------------------------------------------------
        surf = pygame.Surface((size, size))
        surf.fill((28, 25, 22))
        # Heavy riveted plates
        pygame.draw.rect(surf, (50, 45, 40), (4, 4, size - 8, size - 8), 4)
        for bx in [16, size - 20]:
            for by in range(20, size - 20, 40):
                pygame.draw.circle(surf, (90, 80, 70), (bx, by), 4)
                pygame.draw.circle(surf, (150, 140, 130), (bx - 1, by - 1), 2)

        # Massive copper coolant pipe with high-temperature glow
        pygame.draw.rect(surf, (170, 85, 30), (45, 0, 36, size))
        pygame.draw.line(surf, (240, 140, 70), (52, 0), (52, size), 6)
        pygame.draw.line(surf, (255, 220, 160), (52, 0), (52, size), 2)

        # Steam pressure vent grill
        pygame.draw.rect(surf, (16, 15, 14), (105, 45, 110, 95))
        for gy in range(55, 135, 12):
            pygame.draw.line(surf, (90, 85, 80), (112, gy), (208, gy), 3)

        # Flashing red emergency warning beacon
        pygame.draw.circle(surf, (255, 35, 35), (160, 185), 18)
        pygame.draw.circle(surf, (255, 180, 180), (160, 185), 8)
        pygame.draw.circle(surf, (255, 255, 255), (160, 185), 3)
        textures['engineering'] = surf

        # -------------------------------------------------------------
        # 3. CREW HABITATION DECK (Sleek composite, locker seams, cyan glow)
        # -------------------------------------------------------------
        surf = pygame.Surface((size, size))
        surf.fill((32, 36, 46))
        pygame.draw.rect(surf, (55, 62, 78), (8, 8, size - 16, size - 16), 3)
        # Vertical locker seam
        pygame.draw.line(surf, (18, 20, 26), (size // 2, 10), (size // 2, size - 10), 4)
        # Cyan accent light bar
        pygame.draw.rect(surf, (0, 210, 255), (25, 22, size - 50, 10))
        pygame.draw.rect(surf, (240, 255, 255), (35, 24, size - 70, 4))
        # Cabin notice screen
        pygame.draw.rect(surf, (18, 22, 30), (35, 65, 85, 90))
        pygame.draw.rect(surf, (0, 140, 180), (35, 65, 85, 90), 2)
        for ly in range(75, 145, 12):
            pygame.draw.line(surf, (180, 210, 230), (45, ly), (110, ly), 2)
        textures['crew'] = surf

        # -------------------------------------------------------------
        # 4. MEDICAL BAY (Sterile cyan/white, diagnostic monitors, frost)
        # -------------------------------------------------------------
        surf = pygame.Surface((size, size))
        surf.fill((30, 42, 50))
        pygame.draw.rect(surf, (50, 72, 85), (6, 6, size - 12, size - 12), 3)
        # Medical cross insignia
        pygame.draw.rect(surf, (0, 235, 255), (size // 2 - 8, 25, 16, 45))
        pygame.draw.rect(surf, (0, 235, 255), (size // 2 - 24, 40, 48, 16))
        # Diagnostic screen
        pygame.draw.rect(surf, (10, 24, 30), (30, 95, size - 60, 90))
        pygame.draw.rect(surf, (0, 180, 220), (30, 95, size - 60, 90), 2)
        # Animated EKG heart rhythm trace
        pts = [(36, 140), (80, 140), (95, 110), (110, 170), (125, 125), (140, 140), (220, 140)]
        pygame.draw.lines(surf, (0, 255, 190), False, pts, 3)
        textures['medical'] = surf

        # -------------------------------------------------------------
        # 5. RESTRICTED LAB / CRYO CORRIDOR (Matching User Concept Image 2)
        # Violet/magenta and cyan neon, floor-embedded diagnostic HUDs
        # -------------------------------------------------------------
        surf = pygame.Surface((size, size))
        surf.fill((24, 20, 36))  # Moody dark violet-metallic base

        # Diagonal reinforcement ribs
        pygame.draw.line(surf, (55, 45, 75), (0, 0), (size, size), 4)
        pygame.draw.line(surf, (55, 45, 75), (size, 0), (0, size), 4)
        pygame.draw.rect(surf, (40, 32, 58), (12, 12, size - 24, size - 24), 3)

        # Glowing cyan and magenta neon tube fixtures (Image 2 style)
        pygame.draw.line(surf, (0, 220, 255), (35, 0), (35, size), 6)
        pygame.draw.line(surf, (240, 255, 255), (35, 0), (35, size), 2)
        pygame.draw.line(surf, (230, 60, 255), (size - 35, 0), (size - 35, size), 6)
        pygame.draw.line(surf, (255, 210, 255), (size - 35, 0), (size - 35, size), 2)

        # Floor-embedded diagnostic monitor screen (Image 2 style)
        pygame.draw.rect(surf, (15, 12, 28), (55, 140, size - 110, 80))
        pygame.draw.rect(surf, (195, 70, 255), (55, 140, size - 110, 80), 3)
        # Waveform inside floor screen
        for wy in range(155, 210, 14):
            pygame.draw.line(surf, (0, 240, 255), (65, wy), (size - 65, wy), 2)
        pygame.draw.circle(surf, (255, 80, 200), (size // 2, 180), 12)

        # Biohazard radiation symbol
        center = (size // 2, 60)
        pygame.draw.circle(surf, (255, 185, 20), center, 24, 4)
        pygame.draw.circle(surf, (255, 185, 20), (center[0] - 8, center[1] - 5), 10, 3)
        pygame.draw.circle(surf, (255, 185, 20), (center[0] + 8, center[1] - 5), 10, 3)
        pygame.draw.circle(surf, (255, 185, 20), (center[0], center[1] + 9), 10, 3)
        textures['lab'] = surf

        # -------------------------------------------------------------
        # 6. CORE VAULT (Obsidian alien composite, pulsing violet circuits)
        # -------------------------------------------------------------
        surf = pygame.Surface((size, size))
        surf.fill((16, 12, 24))
        pygame.draw.rect(surf, (36, 26, 52), (8, 8, size - 16, size - 16), 3)
        # Alien geometric glyphs & violet conduits
        pts = [(0, 40), (60, 40), (100, 100), (160, 100), (200, 160), (size, 160)]
        pygame.draw.lines(surf, (195, 65, 255), False, pts, 4)
        pygame.draw.lines(surf, (255, 220, 255), False, pts, 2)
        pygame.draw.circle(surf, (210, 100, 255), (100, 100), 14)
        pygame.draw.circle(surf, (255, 255, 255), (100, 100), 5)
        pygame.draw.circle(surf, (210, 100, 255), (200, 160), 14)
        pygame.draw.circle(surf, (255, 255, 255), (200, 160), 5)
        textures['vault'] = surf

        # -------------------------------------------------------------
        # 7. COMMUNICATIONS DECK (Server racks, signal oscilloscopes)
        # -------------------------------------------------------------
        surf = pygame.Surface((size, size))
        surf.fill((24, 28, 34))
        pygame.draw.rect(surf, (44, 52, 64), (6, 6, size - 12, size - 12), 3)
        # Server blade banks
        for sy in range(25, size - 25, 34):
            pygame.draw.rect(surf, (14, 16, 20), (22, sy, size - 44, 24))
            pygame.draw.circle(surf, (0, 255, 130), (34, sy + 12), 4)
            pygame.draw.circle(surf, (255, 175, 20), (48, sy + 12), 4)
            pygame.draw.circle(surf, (0, 220, 255), (62, sy + 12), 4)
            pygame.draw.line(surf, (60, 75, 90), (80, sy + 12), (size - 35, sy + 12), 2)
        textures['comms'] = surf

        # -------------------------------------------------------------
        # 8. OBSERVATION DOME WINDOW (Deep space stars & void)
        # -------------------------------------------------------------
        surf = pygame.Surface((size, size))
        surf.fill((4, 4, 12))
        rnd = random.Random(1337)
        for _ in range(80):
            sx = rnd.randint(18, size - 18)
            sy = rnd.randint(18, size - 18)
            b = rnd.randint(140, 255)
            surf.set_at((sx, sy), (b, b, min(255, b + 30)))
        # Nebula glow
        neb = pygame.Surface((100, 100), pygame.SRCALPHA)
        pygame.draw.circle(neb, (80, 20, 120, 60), (50, 50), 45)
        surf.blit(neb, (size // 2 - 50, size // 2 - 50))
        # Titanium viewport frame
        pygame.draw.rect(surf, (45, 52, 68), (0, 0, size, size), 18)
        pygame.draw.rect(surf, (75, 88, 110), (14, 14, size - 28, size - 28), 3)
        textures['observation'] = surf

        # -------------------------------------------------------------
        # 9. CONTINUUM ENGINE CHAMBER (Quantum crystalline core)
        # -------------------------------------------------------------
        surf = pygame.Surface((size, size))
        surf.fill((12, 10, 22))
        pts = [(size // 2, 10), (size - 15, size // 2), (size // 2, size - 10), (15, size // 2)]
        pygame.draw.polygon(surf, (30, 20, 50), pts)
        pygame.draw.polygon(surf, (190, 75, 255), pts, 4)
        pygame.draw.circle(surf, (220, 130, 255), (size // 2, size // 2), 24)
        pygame.draw.circle(surf, (255, 255, 255), (size // 2, size // 2), 10)
        textures['engine'] = surf

        # -------------------------------------------------------------
        # 10. HEAVY BLAST DOOR — LOCKED (Matching User Concept Image 3)
        # Segmented interlocking plates, orange/red lamps, caution trims
        # -------------------------------------------------------------
        surf = pygame.Surface((size, size))
        surf.fill((32, 36, 44))  # Heavy armor plate gray

        # Outer door frame with yellow/black caution diagonals
        for ch in range(0, size, 24):
            pygame.draw.polygon(surf, (255, 175, 20), [(0, ch), (14, ch + 8), (14, ch + 16), (0, ch + 8)])
            pygame.draw.polygon(surf, (255, 175, 20), [(size - 14, ch), (size, ch + 8), (size, ch + 16), (size - 14, ch + 8)])

        # Interlocking horizontal segmented blast panels (Image 3 style)
        pygame.draw.line(surf, (12, 14, 18), (size // 2, 0), (size // 2, size), 6)  # Split seam
        for py_step in [30, 90, 150, 210]:
            pygame.draw.rect(surf, (48, 54, 66), (18, py_step, size - 36, 48))
            pygame.draw.rect(surf, (20, 24, 30), (18, py_step, size - 36, 48), 2)
            # Bevel highlights
            pygame.draw.line(surf, (80, 90, 110), (20, py_step + 2), (size - 20, py_step + 2), 2)

        # Central hydraulic interlocking locking mechanism
        pygame.draw.rect(surf, (24, 28, 36), (size // 2 - 35, size // 2 - 40, 70, 80), border_radius=6)
        pygame.draw.rect(surf, (255, 45, 45), (size // 2 - 35, size // 2 - 40, 70, 80), 3, border_radius=6)

        # Glowing red status beacon and warning icon
        pygame.draw.circle(surf, (255, 40, 40), (size // 2, size // 2), 16)
        pygame.draw.circle(surf, (255, 200, 200), (size // 2, size // 2), 6)
        # Red warning lamps at top corners (Image 3 style)
        pygame.draw.circle(surf, (255, 40, 40), (38, 25), 8)
        pygame.draw.circle(surf, (255, 40, 40), (size - 38, 25), 8)
        textures['door_locked'] = surf

        # -------------------------------------------------------------
        # 11. HEAVY BLAST DOOR — UNLOCKED (Green portal indicators)
        # -------------------------------------------------------------
        surf = pygame.Surface((size, size))
        surf.fill((25, 38, 30))
        pygame.draw.line(surf, (10, 18, 12), (size // 2, 0), (size // 2, size), 6)
        for py_step in [30, 90, 150, 210]:
            pygame.draw.rect(surf, (35, 58, 45), (18, py_step, size - 36, 48))
            pygame.draw.rect(surf, (15, 28, 20), (18, py_step, size - 36, 48), 2)
        # Central lock in green online state
        pygame.draw.rect(surf, (20, 45, 30), (size // 2 - 35, size // 2 - 40, 70, 80), border_radius=6)
        pygame.draw.rect(surf, (40, 255, 130), (size // 2 - 35, size // 2 - 40, 70, 80), 3, border_radius=6)
        pygame.draw.circle(surf, (40, 255, 130), (size // 2, size // 2), 16)
        pygame.draw.circle(surf, (220, 255, 230), (size // 2, size // 2), 6)
        pygame.draw.circle(surf, (40, 255, 130), (38, 25), 8)
        pygame.draw.circle(surf, (40, 255, 130), (size - 38, 25), 8)
        textures['door_unlocked'] = surf

        # -------------------------------------------------------------
        # 12. INTERACTIVE COMPUTER TERMINAL CONSOLE
        # -------------------------------------------------------------
        surf = pygame.Surface((size, size))
        surf.fill((28, 32, 42))
        pygame.draw.rect(surf, (50, 58, 75), (6, 6, size - 12, size - 12), 4)
        # Glowing holographic screen
        pygame.draw.rect(surf, (0, 45, 75), (25, 25, size - 50, 110))
        pygame.draw.rect(surf, (0, 220, 255), (25, 25, size - 50, 110), 3)
        for ly in range(38, 125, 12):
            pygame.draw.line(surf, (0, 240, 255), (38, ly), (size - 38, ly), 2)
        # Tactile keyboard & keycard slot
        pygame.draw.rect(surf, (18, 22, 28), (30, 155, size - 60, 60))
        for kx in range(40, size - 40, 18):
            pygame.draw.rect(surf, (0, 180, 220), (kx, 165, 10, 10))
            pygame.draw.rect(surf, (0, 180, 220), (kx, 185, 10, 10))
        textures['terminal'] = surf

        # -------------------------------------------------------------
        # 13. ALARM / DISTRACTION PANEL
        # -------------------------------------------------------------
        surf = pygame.Surface((size, size))
        surf.fill((35, 32, 24))
        pygame.draw.rect(surf, (75, 68, 45), (6, 6, size - 12, size - 12), 4)
        pygame.draw.circle(surf, (255, 185, 20), (size // 2, size // 2), 38)
        pygame.draw.circle(surf, (255, 255, 130), (size // 2, size // 2), 20)
        pygame.draw.circle(surf, (255, 40, 40), (size // 2, size // 2), 8)
        textures['distraction'] = surf

        return textures
