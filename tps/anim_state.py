"""Chooses which rig action to play from the player's state (pure Python)."""
from dataclasses import dataclass


@dataclass
class AnimInput:
    stance: str = "stand"         # stand | crouch | sit
    moving: bool = False
    sprinting: bool = False
    airborne: bool = False
    aiming: bool = False
    weapon_kind: str = "ranged"   # ranged | melee
    aim_anim: str = "aim_pistol"
    reloading: bool = False
    reload_anim: str = ""
    meleeing: bool = False


ONE_SHOT = {"melee_slash", "jump", "reload_pistol", "reload_rifle"}


def pick_animation(a: AnimInput) -> str:
    if a.meleeing:
        return "melee_slash"
    if a.reloading and a.reload_anim:
        return a.reload_anim
    if a.airborne:
        return "jump"
    if a.stance == "sit":
        return "sit"
    ranged_aim = a.aiming and a.weapon_kind == "ranged"
    if a.stance == "crouch":
        if a.moving:
            return "crouch_walk"
        return a.aim_anim if ranged_aim else "crouch_idle"
    if a.moving:
        return "sprint" if a.sprinting else "walk"
    return a.aim_anim if ranged_aim else "idle"
