"""Launch the Sector9 third-person prototype.

    python run_tps.py              # play
    python run_tps.py --selftest   # scripted, windowless check of controls/weapons/animations
    python run_tps.py --no-shadows # if the GPU is slow
Assets are read from assets/models/*.glb (see tools/blender_assets/build_all.py);
if missing, simple placeholder boxes are used so the controls can still be tested.
"""
import argparse
import sys


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--no-shadows", action="store_true")
    ap.add_argument("--seed", type=int, default=None)
    a = ap.parse_args()
    try:
        from tps.game import Sector9TPS
    except ImportError as e:
        sys.exit(f"Missing dependency ({e}). Run: pip install -r requirements-3d.txt")
    app = Sector9TPS(selftest=a.selftest, shadows=not a.no_shadows, seed=a.seed)
    if a.selftest:
        sys.exit(0 if app.run_selftest() else 1)
    app.run()


if __name__ == "__main__":
    main()
