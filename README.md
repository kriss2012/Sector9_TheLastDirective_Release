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

7. **Space Lobby Hub (Doors, Locks & Missions)**:
   - A walkable corridor hub with animated sliding blast doors and five lock types (free, keycard, keypad code, power-gated, containment lockdown). See [Space Lobby](#space-lobby) below.

8. **Persistence & Save System**:
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

Jump straight into the space lobby:
```bash
python main.py --lobby
```
(or choose **SPACE LOBBY** in the main menu).

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

## Space Lobby

A central transit corridor with eight doors. It is a self-contained mission chain that
ends by launching into Chapter 1. Textures are procedural, modelled on the concept art
(orange "Level 07" corridor, blue-silver viewport corridor, white SPACE-CORPS tube,
hazard-stripe blast door, dark armoured door).

```
       0         1         2
       0123456789012345678901234567
  y0   #########T###############ZZ#     T = Mission Board
  y1   #...#.........#.......#....#
  y2   #...#.........#.......#....#     north rooms: Supply Locker, Mission Control,
  y3   ##D###Z##D####Z####D###DZ###                  Engineering Annex, Observation Lounge
  y4   #..........................#
  y5   #..........................D     east end: Launch Airlock
  y6   #..........................#
  y7   ##D###T##D####Z####D########     T = Auxiliary Power Node
  y8   #...#.........#.........####     south rooms: Crew Quarters, Airlock Bay, Hangar
  y9   #...#.........#.........####
```

### Mission chain

| # | Step | Lock type used |
|---|------|----------------|
| 1 | Supply Locker -> take **Level-1 Keycard** | none (just a closed door) |
| 2 | Mission Control -> accept the mission at the board, learn the annex code | **keycard** |
| 3 | Engineering Annex -> enter the code on the keypad, take the **Power Cell** | **keypad** (3 wrong tries = 4 s lockout) |
| 4 | Install the Power Cell at the Auxiliary Power Node (corridor) | - |
| 5 | Airlock Bay -> take the **Level-2 Keycard** | **power-gated** (dark door until power is restored) |
| 6 | Hangar Gate -> take the **Mission Data Chip** | **keycard** |
| 7 | Taking the chip triggers a **12 s containment lockdown**: every door seals | **lockdown** |
| 8 | Lockdown lifts, the Launch Airlock comes online -> launch to Chapter 1 | **flag** |

Doors never close on the player: a door holds open while you stand in the doorway, and a
lockdown waits for you to step clear before sealing. Doors you unlocked stay unlocked after
saving and loading, and pickups you took do not respawn.

### How the door states look
- **Red lamps / dark panel**: locked (keycard or keypad / no power)
- **Yellow-black hazard stripes with teal windows**: unlocked, closed
- The door leaf slides up into the ceiling as it opens, with a pneumatic hiss.

### Adding your own doors and missions
- **Layout, doors, pickups**: `src/lobby_layout.py` (`build_grid`, `build_doors`, `SPRITES`).
- **Rules** (what each door/terminal/pickup does): `src/lobby_logic.py`.
- **Door state machine and lockdown**: `src/door_system.py`
  (`Door(id, cell, label, lock_type, requires=..., code=...)`).
- **Objectives and journal text**: `assets/data/chapters.json` (chapter `"7"`) and `assets/data/lore_logs.json`.
- The first three files import no pygame, so they are unit-tested without a display
  (`tests/test_lobby_logic.py`). The pygame glue is `src/lobby.py`.

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
│   ├── door_system.py             # Door state machine, lock types & containment lockdown (pure Python)
│   ├── engine.py                  # Master GameEngine state machine
│   ├── levels.py                  # Deck map grids, entities & interactive triggers
│   ├── lobby.py                   # Space lobby pygame glue: level build, keypad UI, lockdown overlay
│   ├── lobby_layout.py            # Space lobby map, doors, pickups & wall styles (pure Python)
│   ├── lobby_logic.py             # Space lobby mission rules & prompts (pure Python)
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
│   ├── test_lobby_logic.py        # Lobby doors, locks, layout & full mission playthrough (no pygame needed)
│   ├── test_puzzles.py            # Unit tests for all 7 puzzles
│   ├── test_quests.py             # Quest progression & level loading tests
│   └── test_save_load.py          # Save & load round-trip persistence tests
├── main.py                        # Primary entry point
├── run_game.py                    # Legacy entry point wrapper
├── requirements.txt
└── README.md
```
