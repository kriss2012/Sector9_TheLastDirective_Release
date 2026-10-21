"""Procedural sound effects written to WAV (stdlib only). Replace any file in
assets/sfx with your own recording using the same name and the game will use it.
"""
import math
import os
import random
import struct
import wave

RATE = 44100


def _write(path, samples):
    peak = max(1e-9, max(abs(s) for s in samples))
    data = b"".join(struct.pack("<h", int(max(-1, min(1, s / peak * 0.9)) * 32767)) for s in samples)
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(RATE)
        w.writeframes(data)


def _noise_env(dur, decay, rng, lowpass=0.0):
    n, out, prev = int(dur * RATE), [], 0.0
    for i in range(n):
        x = rng.uniform(-1, 1)
        prev = lowpass * prev + (1 - lowpass) * x
        out.append(prev * math.exp(-i / RATE * decay))
    return out


def _tone(freq, dur, decay, start_freq=None):
    out, ph = [], 0.0
    n = int(dur * RATE)
    for i in range(n):
        f = freq if start_freq is None else start_freq + (freq - start_freq) * i / n
        ph += 2 * math.pi * f / RATE
        out.append(math.sin(ph) * math.exp(-i / RATE * decay))
    return out


def _mix(*tracks):
    n = max(len(t) for t in tracks)
    return [sum(t[i] for t in tracks if i < len(t)) for i in range(n)]


def _delay(track, secs):
    return [0.0] * int(secs * RATE) + track


def generate_all(out_dir):
    os.makedirs(out_dir, exist_ok=True)
    rng = random.Random(7)
    files = {
        "pistol_fire.wav": _mix([s * 1.0 for s in _noise_env(0.45, 11, rng, 0.35)],
                                [s * 0.9 for s in _tone(60, 0.3, 14, 180)]),
        "rifle_fire.wav": _mix([s * 1.0 for s in _noise_env(0.30, 16, rng, 0.2)],
                               [s * 0.8 for s in _tone(80, 0.2, 22, 240)]),
        "dry_click.wav": _mix(_noise_env(0.04, 120, rng, 0.0), _tone(1800, 0.03, 150)),
        "reload_start.wav": _mix(_noise_env(0.06, 80, rng, 0.5), _tone(700, 0.05, 90)),
        "reload_end.wav": _mix(_noise_env(0.08, 60, rng, 0.4),
                               _delay(_noise_env(0.05, 90, rng, 0.2), 0.10)),
        "switch.wav": _mix(_noise_env(0.10, 40, rng, 0.7), _tone(300, 0.08, 40, 500)),
        "melee_swing.wav": [s * (0.6 + 0.4 * math.sin(i / RATE * 18)) for i, s in
                            enumerate(_noise_env(0.35, 6, rng, 0.85))],
        "melee_hit.wav": _mix(_noise_env(0.12, 50, rng, 0.5), _tone(180, 0.15, 25)),
        "hit_marker.wav": _tone(1200, 0.07, 45),
        "impact.wav": _noise_env(0.08, 55, rng, 0.6),
        "footstep.wav": _noise_env(0.10, 45, rng, 0.9),
        "jump.wav": _mix(_noise_env(0.08, 35, rng, 0.9), _tone(250, 0.1, 25, 160)),
        "land.wav": _mix(_noise_env(0.12, 30, rng, 0.9), _tone(90, 0.12, 30)),
        "target_down.wav": _mix(_tone(500, 0.3, 8, 900), _noise_env(0.05, 70, rng, 0.3)),
    }
    for name, samples in files.items():
        path = os.path.join(out_dir, name)
        if not os.path.exists(path):          # never overwrite user-supplied sounds
            _write(path, samples)
    return sorted(files)


if __name__ == "__main__":
    import sys
    print(generate_all(sys.argv[1] if len(sys.argv) > 1 else "assets/sfx"))
