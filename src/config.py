import os
import sys
import pygame

# Default Screen & Rendering
SCREEN_WIDTH = 1280
SCREEN_HEIGHT = 720
RENDER_WIDTH = 640
RENDER_HEIGHT = 360
FPS = 60

# FOV & Raycasting
FOV = 1.15  # ~66 degrees in radians for immersive modern FOV
HALF_FOV = FOV / 2.0
MAX_DEPTH = 22.0
MOUSE_SENSITIVITY = 0.0016
PLAYER_SPEED = 3.2
PLAYER_RUN_SPEED = 4.8
PLAYER_ROT_SPEED = 2.4
PLAYER_RADIUS = 0.22

# Suit & Systems
MAX_HEALTH = 100.0
MAX_FLASHLIGHT = 100.0
FLASHLIGHT_DRAIN_RATE = 0.6
FLASHLIGHT_RECHARGE_RATE = 1.8

# Sci-Fi Colors
COLOR_BLACK = (0, 0, 0)
COLOR_WHITE = (255, 255, 255)
COLOR_DARK_GRAY = (18, 20, 26)
COLOR_MID_GRAY = (48, 52, 64)
COLOR_LIGHT_GRAY = (190, 200, 215)

COLOR_CYAN = (0, 225, 255)
COLOR_CYAN_DIM = (0, 110, 150)
COLOR_CYAN_GLOW = (140, 245, 255)

COLOR_AMBER = (255, 175, 20)
COLOR_AMBER_DIM = (160, 95, 10)
COLOR_AMBER_GLOW = (255, 210, 90)

COLOR_ALERT_RED = (255, 45, 45)
COLOR_ALERT_RED_DIM = (130, 20, 20)

COLOR_ALIEN_VIOLET = (195, 75, 255)
COLOR_ALIEN_VIOLET_DIM = (95, 25, 140)
COLOR_ALIEN_VIOLET_GLOW = (230, 150, 255)

COLOR_GREEN = (40, 255, 130)
COLOR_GREEN_DIM = (20, 140, 60)
COLOR_GREEN_GLOW = (130, 255, 180)

# Paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BUNDLE_DIR = getattr(sys, '_MEIPASS', BASE_DIR)
DATA_DIR = os.path.join(BUNDLE_DIR, "assets", "data")
IMAGES_DIR = os.path.join(BUNDLE_DIR, "assets", "images")

if getattr(sys, 'frozen', False):
    EXE_DIR = os.path.dirname(sys.executable)
    SAVES_DIR = os.path.join(EXE_DIR, "assets", "saves")
else:
    SAVES_DIR = os.path.join(BASE_DIR, "assets", "saves")
