"""Throw-away test arena. Replace `build_world()` with your real level later:
anything that returns a physics.World (plus an optional name->colour map) works.
"""
from .physics import World


def build_world():
    w = World(ground_z=0.0)
    colors = {}

    def add(name, lo, hi, color, hp=None):
        w.add_box(name, lo, hi, hp)
        colors[name] = color

    add("wall_north", (-20, 24, 0), (20, 25, 5), (0.30, 0.32, 0.36, 1))
    add("wall_east", (24, -20, 0), (25, 25, 5), (0.30, 0.32, 0.36, 1))
    add("wall_west", (-25, -20, 0), (-24, 25, 5), (0.30, 0.32, 0.36, 1))
    add("crate_a", (3, 4, 0), (4.2, 5.2, 1.2), (0.35, 0.25, 0.12, 1))
    add("crate_b", (-4, 6, 0), (-2.6, 7.4, 1.4), (0.35, 0.25, 0.12, 1))
    add("step_low", (6, 2, 0), (9, 4, 0.25), (0.25, 0.25, 0.28, 1))       # walk up (step height)
    add("platform", (6, 8, 0), (10, 12, 1.0), (0.22, 0.22, 0.26, 1))      # too tall: jump onto it
    # Low beam: crouch under it (1.3 m clearance)
    add("beam", (-10, 2, 1.3), (-6, 3, 1.6), (0.40, 0.18, 0.10, 1))
    add("beam_post_l", (-10, 2, 0), (-9.7, 3, 1.3), (0.30, 0.15, 0.08, 1))
    add("beam_post_r", (-6.3, 2, 0), (-6, 3, 1.3), (0.30, 0.15, 0.08, 1))
    # Shooting range
    for i, x in enumerate((-6, -2, 2, 6, 10)):
        add(f"target_{i}", (x - 0.4, 18, 0), (x + 0.4, 18.3, 1.9), (0.8, 0.15, 0.12, 1), hp=100)
    for i, x in enumerate((-4, 4)):
        add(f"target_far_{i}", (x - 0.4, 22, 0), (x + 0.4, 22.3, 1.9), (0.9, 0.5, 0.1, 1), hp=150)
    return w, colors
