import os
import sys

if sys.platform == 'win32':
    try:
        import ctypes
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass

import argparse
import logging

# Set path to include current directory
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Setup file logging so we can capture output even in fullscreen
LOG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "game_debug.log")
logging.basicConfig(
    filename=LOG_FILE,
    level=logging.DEBUG,
    format='%(asctime)s [%(levelname)s] %(message)s',
    filemode='w'
)
logger = logging.getLogger("Sector9")

import pygame
from src.config import FPS
from src.engine import GameEngine

def main():
    parser = argparse.ArgumentParser(description="Sector 9: The Last Directive")
    parser.add_argument("--headless", action="store_true", help="Run without graphical display (for testing)")
    args = parser.parse_args()

    # Headless check
    if 'COLAB_GPU' in os.environ or 'google.colab' in sys.modules:
        args.headless = True

    print("==================================================")
    print("SECTOR 9: THE LAST DIRECTIVE")
    print("UNSC Aegis-9 Command Dreadnought // Deep Space 2847")
    print("==================================================")
    logger.info("Game starting...")

    game = GameEngine(headless=args.headless)
    logger.info(f"Engine initialized. Screen: {game.screen_width}x{game.screen_height}, Fullscreen: {game.is_fullscreen}")

    # If headless, run a self-test tick and exit gracefully
    if args.headless:
        print("[Headless Mode] Executing engine self-test ticks...")
        for _ in range(10):
            game.update(1.0 / FPS)
        print("[Headless Mode] Self-test passed successfully.")
        return

    # Standard 60 FPS Game Loop
    prev_state = game.state
    running = True
    frame = 0
    while running:
        dt = game.clock.tick(FPS) / 1000.0
        frame += 1
        try:
            game.handle_events()
            game.update(dt)
            game.draw()

            # Log state transitions
            if game.state != prev_state:
                logger.info(f"Frame {frame}: State changed: {prev_state} -> {game.state}")
                prev_state = game.state
        except SystemExit:
            logger.info(f"Frame {frame}: SystemExit received, shutting down")
            running = False
        except Exception as e:
            logger.error(f"Frame {frame}: Error in game loop: {e}", exc_info=True)
            print(f"[GameEngine] Error in game loop: {e}")
            import traceback
            traceback.print_exc()

    logger.info("Game loop ended.")

if __name__ == "__main__":
    main()
