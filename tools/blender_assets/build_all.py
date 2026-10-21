"""Build every Sector9 asset by launching Blender once per script.

    python tools/blender_assets/build_all.py --blender "C:/Program Files/Blender Foundation/Blender 4.2/blender.exe" --out assets/models

Without --blender it uses `blender` from PATH.  Outputs (.blend + .glb):
  pistol_m1911, rifle_carbine, knife_kukri, character_operator
"""
import argparse
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = ["build_pistol.py", "build_rifle.py", "build_kukri.py", "build_character.py"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--blender", default="blender")
    ap.add_argument("--out", default="assets/models")
    a = ap.parse_args()
    failed = []
    for s in SCRIPTS:
        print(f"=== {s} ===", flush=True)
        r = subprocess.run([a.blender, "--background", "--python", os.path.join(HERE, s),
                            "--", "--out", a.out])
        if r.returncode != 0:
            failed.append(s)
    print("FAILED:" if failed else "All assets built.", ", ".join(failed))
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
