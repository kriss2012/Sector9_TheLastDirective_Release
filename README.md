# SECTOR 9: THE LAST DIRECTIVE

**First-Person Sci-Fi Warship Adventure, Mystery, and Exploration**  
*Built with Python 3, Pygame, and procedural audio synthesis.*

---

## Overview

In the year 2847, humanity's largest warship, the 4-kilometer **UNSC Aegis-9**, receives an impossible distress signal from its own future carrying the voice of Commander Clara Voss. Simultaneously, stars begin vanishing from celestial records—not exploding, but being erased from causality as if they never existed.

When the ship's commander, Captain Elias Ward, is killed in an attack by an ancient alien machine intelligence known as **The Watcher**, Commander Clara Voss must take command of the damaged dreadnought, stabilize critical ship systems, uncover classified secrets behind the vanished Veyr civilization, and decide the ultimate fate of existence across a six-chapter campaign.

---

## Key Features

1. **First-Person Pseudo-3D Engine**:
   - High-performance DDA (Digital Differential Analyzer) raycaster with per-column texture mapping, directional depth shading, and distance fog.
   - Dynamic flashlight cone lighting and suit battery management.
   - 2.5D Billboarding sprite system with depth buffering for items, consoles, fallen crew, drones, and alien holograms.

2. **Full Six-Chapter Campaign & Prologue**:
   - **Prologue: The Ship That Heard Tomorrow** (Command Bridge)
   - **Chapter 1: Systems Offline** (Engineering Deck & Life Support)
   - **Chapter 2: Dead Echoes** (Habitation Deck & Medical Wing)
   - **Chapter 3: Containment Breach** (Restricted Xenotech Laboratory & Sector 9 Core)
   - **Chapter 4: The Core Vault** (Automated Defense Matrix & Ward's Archive)
   - **Chapter 5: Whispers in the Dark** (Observation Dome & Orbital Communications)
   - **Chapter 6: Final Directive** (Spacetime Distortion & The Continuum Engine)

3. **Seven Dedicated Tactical Puzzles**:
   - **Emergency Power Routing**: Connect Battery -> Voltage Regulator -> Pressure Relay while isolating weapon capacitors.
   - **Medical Locker Keypad**: Derive the 3-digit access code from patient admission logs (`505`).
   - **Biohazard Containment Valves**: Isolate valves in strict sequence: Helix (Lab) -> Circle (Containment) -> Flame (Cooling).
   - **Defense Matrix Reprogramming**: Reconfigure Identity (Voss-9442 Dead Simulation), Command (Ward-Halt-09), and Target (Isolate Core).
   - **Orbital Transceiver Alignment**: Align 3 satellite dishes in Azimuth and Elevation to lock onto deep-space relay beacons.
   - **Quantum Harmonic Resonance (Optional Side Quest)**: Tune 3 resonance harmonic nodes (420 Hz, 840 Hz, 1260 Hz) to reconstruct Dr. Sera Nahl's consciousness.
   - **Prime Directive Console**: Commit the ultimate timeline decision at the central Continuum Engine.

4. **Stealth & Enemy AI**:
   - Watcher Sentry Drones with realistic field-of-view search cones (yellow for search, flashing red for chase).
   - Environmental distraction panels: Trigger sound pulses on junction boxes to lure drones away.
   - Non-instant death / Recoverable failure: Drones deploy electrical stun pulses that damage suit integrity and reset Clara to the section checkpoint.

5. **Four Cinematic Endings**:
   - **Ending A — The Last Light (Hopeful)**: Full system reboot. Clara preserves the universe and human free will.
   - **Ending B — The New Watcher (Sacrifice)**: Neural integration. Clara merges her consciousness into the Engine to replace the Watcher with human empathy.
   - **Ending C — The Final Silence (Dark)**: Complete severance. Clara disconnects the Engine, leaving the 48 vanished systems permanently lost.
   - **Secret Ending — The Universe Remembers (Canon Secret)**: Unlocked by recovering all 3 Veyr memory fragments and completing Dr. Sera Nahl's harmonic synchronization. Broadcasts the compressed history archive across deep space before rebooting the core.

6. **Procedural Sci-Fi Synthesizer (Zero Missing Audio Assets)**:
   - Uses `numpy` and `pygame.mixer` to generate rich sci-fi sounds directly in code: engine hums, alarms, radio bursts, keypad beeps, alien harmonic chords, drone sirens, electrical sparks, footsteps, and character voice blips for Clara, Ward, NOVA, Malik, Sera, and The Watcher.

7. **Persistence & Save System**:
   - Versioned JSON saves storing chapter progress, player coordinates, inventory, discovered audio logs, story flags, and completed objectives.
   - Autosaves at every chapter deployment, plus manual saving and loading via the Pause menu.

---

## Installation & Setup

### Prerequisites
- Python 3.10+ (tested on Python 3.12)
- Pygame 2.6+
- NumPy 1.24+

### Install Dependencies
```bash
pip install -r requirements.txt
```

---

## Running the Game

Launch the game using either command:

```bash
python main.py
```
or
```bash
python run_game.py
```

### Headless Mode (For Automated CI/Testing)
```bash
python main.py --headless
```

---

## Tactical Controls

| Key / Input | Action |
|---|---|
| **W, A, S, D** or **Arrow Keys** | Walk / Strafe |
| **Shift** | Sprint |
| **Mouse** | First-Person Camera Rotation |
| **E** | Interact (Terminals, Doors, Items, Puzzles, Logs) |
| **F** | Toggle Tactical Suit Flashlight |
| **TAB** or **J** | Open Mission Journal (Directives, Discovered Logs, Telemetry) |
| **I** | Open Inventory & Equipment |
| **1, 2, 3** | Switch Journal Tabs |
| **ESC** | Pause Mission / Release Mouse Cursor |

---

## Automated Test Suite

A complete test suite covering puzzles, quests, save/load, and ending prerequisites is provided in `tests/`:

```bash
python tests/run_all_tests.py
```

---

## Project Structure

```
.
├── assets/
│   ├── data/
│   │   ├── chapters.json          # Story progression, chapters 0-6 & objectives
│   │   ├── dialogues.json         # Complete dialogue & radio transmission scripts
│   │   ├── lore_logs.json         # Audio logs, patient charts, technician notes
│   │   ├── puzzles.json           # Puzzle configurations, clues & solutions
│   │   └── endings.json           # Cinematic scripts & epilogues for all 4 endings
│   ├── images/                    # Concept art & backdrops
│   │   ├── bridge_emergency.jpg
│   │   ├── corridor_cyan.jpg
│   │   ├── holo_terminal.jpg
│   │   └── corridor_drone.png
│   └── saves/                     # JSON save game files
├── src/
│   ├── ai_watcher.py              # Watcher drone AI, patrol, FOV stealth & distraction
│   ├── cinematics.py              # Opening cutscenes, chapter deployment & ending screens
│   ├── config.py                  # Colors, resolution, FOV & physics constants
│   ├── dialogue_system.py         # Subtitles, typewriter effect & voice blips
│   ├── engine.py                  # Master GameEngine state machine
│   ├── levels.py                  # Deck map grids, entities & interactive triggers
│   ├── player.py                  # Clara Voss controller, health, flashlight & inventory
│   ├── puzzles.py                 # All 7 interactive sci-fi puzzle interfaces
│   ├── quest_system.py            # Objective tracker, story flags & chapter gating
│   ├── raycaster.py               # DDA raycaster, wall texturing, fog & minimap
│   ├── save_system.py             # Versioned JSON serialization & load routines
│   ├── sound_system.py            # Procedural synthesizer for sci-fi SFX
│   ├── sprite_renderer.py         # 2.5D billboard sprites with depth buffer clipping
│   ├── texture_generator.py       # Procedural 128x128 sci-fi wall & door textures
│   └── ui_manager.py              # Aegis-9 HUD, Journal viewer & Pause menu
├── tests/
│   ├── run_all_tests.py           # Unified test runner
│   ├── test_endings.py            # Ending verification & prerequisite tests
│   ├── test_puzzles.py            # Unit tests for all 7 puzzles
│   ├── test_quests.py             # Quest progression & level loading tests
│   └── test_save_load.py          # Save & load round-trip persistence tests
├── main.py                        # Primary entry point
├── run_game.py                    # Legacy entry point wrapper
├── requirements.txt
└── README.md
```
