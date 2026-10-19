import pygame
from src.sprite_renderer import SpriteObject

class LevelData:
    def __init__(self, chapter_id, map_grid, player_spawn, theme, sprites=None, interactions=None):
        self.chapter_id = chapter_id
        self.map_grid = map_grid
        self.player_spawn = player_spawn
        self.theme = theme
        self.sprites = sprites or []
        self.interactions = interactions or {}

class LevelManager:
    @staticmethod
    def get_level(chapter_id):
        if chapter_id == 0:
            return LevelManager._build_prologue()
        elif chapter_id == 1:
            return LevelManager._build_chapter_1()
        elif chapter_id == 2:
            return LevelManager._build_chapter_2()
        elif chapter_id == 3:
            return LevelManager._build_chapter_3()
        elif chapter_id == 4:
            return LevelManager._build_chapter_4()
        elif chapter_id == 5:
            return LevelManager._build_chapter_5()
        elif chapter_id == 6:
            return LevelManager._build_chapter_6()
        return LevelManager._build_prologue()

    # ========================================================
    # CHAPTER 0: PROLOGUE — COMMAND BRIDGE & HANGAR CORRIDOR
    # ========================================================
    @staticmethod
    def _build_prologue():
        grid = [
            "##############",
            "#P...#.......#",
            "#.T..#...C...#",
            "#....#.......#",
            "###D##########",
            "#............#",
            "#.T....E.....#",
            "##############"
        ]
        # P: Spawn at (1.5, 1.5)
        # T at (2, 2): Damaged Bridge Console (Hale's chip)
        # C at (9, 2): Fallen officer with Emergency Access Card (marked as objective beacon!)
        # D at (3, 4): Bridge Security Door (Supports Card Scan OR Password '2847'!)
        # E at (7, 6): Engineering Lift to Deck 04
        sprites = [
            SpriteObject(9.5, 2.5, 'fallen_crew', entity_id='fallen_officer', interactive=True, label="[E] Retrieve Emergency Access Card", is_objective=True),
            SpriteObject(2.5, 2.5, 'chip', entity_id='hale_chip_sprite', interactive=True, label="[E] Read Damaged Console", is_objective=True),
            SpriteObject(7.5, 2.5, 'cryo_capsule', entity_id='bridge_cryo', interactive=False)
        ]
        interactions = {
            (2, 2): {"type": "console", "id": "bridge_console"},
            (9, 2): {"type": "item", "item": "Emergency Access Card", "id": "access_card"},
            (3, 4): {"type": "door_puzzle", "id": "bridge_door"},
            (7, 6): {"type": "lift", "next_chapter": 1, "id": "lift_deck_04"}
        }
        return LevelData(0, grid, (1.5, 1.5, 0.0), 'bridge', sprites, interactions)

    # ========================================================
    # CHAPTER 1: SYSTEMS OFFLINE — ENGINEERING DECK
    # ========================================================
    @staticmethod
    def _build_chapter_1():
        grid = [
            "################",
            "#P....#........#",
            "#..H..#...T....#",
            "#.....#........#",
            "####D###########",
            "#......#...W...#",
            "#.X....#.......#",
            "#......#...E...#",
            "################"
        ]
        sprites = [
            SpriteObject(3.5, 2.5, 'hazard', entity_id='spark_hazard', interactive=False),
            SpriteObject(11.5, 5.5, 'tool', entity_id='tool_sprite', interactive=True, label="[E] Retrieve Maintenance Tool", is_objective=True),
            SpriteObject(2.5, 6.5, 'chip', entity_id='malik_log_sprite', interactive=True, label="[E] Malik's Audio Terminal")
        ]
        interactions = {
            (10, 2): {"type": "puzzle", "puzzle_name": "power_routing", "id": "power_panel"},
            (11, 5): {"type": "item", "item": "Maintenance Tool", "id": "maint_tool"},
            (2, 6): {"type": "lore", "lore_key": "malik_personal_log", "id": "malik_log"},
            (4, 4): {"type": "door", "requires_flag": "power_restored", "id": "eng_door"},
            (11, 7): {"type": "lift", "next_chapter": 2, "id": "lift_deck_02"}
        }
        return LevelData(1, grid, (1.5, 1.5, 0.0), 'engineering', sprites, interactions)

    # ========================================================
    # CHAPTER 2: DEAD ECHOES — CREW QUARTERS & MEDICAL BAY
    # ========================================================
    @staticmethod
    def _build_chapter_2():
        grid = [
            "##################",
            "#P.....#.........#",
            "#.M....#...L.....#",
            "#......#.........#",
            "####D#############",
            "#......#...#.....#",
            "#.X....#...#..D..#",
            "#......#...#..E..#",
            "##################"
        ]
        sprites = [
            SpriteObject(2.5, 2.5, 'chip', entity_id='med_records_sprite', interactive=True, label="[E] Patient Medical Records", is_objective=True),
            SpriteObject(11.5, 2.5, 'badge', entity_id='locker_sprite', interactive=True, label="[E] Science Director's Locker", is_objective=True)
        ]
        interactions = {
            (2, 2): {"type": "lore", "lore_key": "ch2_patient_records", "id": "med_records"},
            (11, 2): {"type": "puzzle", "puzzle_name": "medical_keypad", "id": "med_locker"},
            (2, 6): {"type": "distraction", "id": "panel_distract"},
            (4, 4): {"type": "door", "requires_flag": "medical_unlocked", "id": "med_door"},
            (14, 6): {"type": "door", "requires": "Science Director's Badge", "id": "central_security_door"},
            (14, 7): {"type": "lift", "next_chapter": 3, "id": "lift_deck_06"}
        }
        return LevelData(2, grid, (1.5, 1.5, 0.0), 'medical', sprites, interactions)

    # ========================================================
    # CHAPTER 3: CONTAINMENT BREACH — RESTRICTED LAB (Image 2 style)
    # ========================================================
    @staticmethod
    def _build_chapter_3():
        grid = [
            "##################",
            "#P.....#.........#",
            "#.F....#...V.....#",
            "#......#.........#",
            "####D#############",
            "#......#...#.....#",
            "#.A....#...#..E..#",
            "##################"
        ]
        sprites = [
            SpriteObject(2.5, 2.5, 'filter', entity_id='filter_station_sprite', interactive=True, label="[E] Fabricate Hazard-Filter", is_objective=True),
            SpriteObject(11.5, 2.5, 'chip', entity_id='valve_terminal_sprite', interactive=True, label="[E] Biohazard Valve Panel", is_objective=True),
            SpriteObject(2.5, 6.5, 'chip', entity_id='veyr_frag_1_sprite', interactive=True, label="[E] Veyr Memory Fragment 1"),
            SpriteObject(9.5, 2.5, 'cryo_capsule', entity_id='lab_cryo', interactive=False)
        ]
        interactions = {
            (2, 2): {"type": "item", "item": "Hazard-Filter Upgrade", "id": "filter_fab"},
            (11, 2): {"type": "puzzle", "puzzle_name": "biohazard_valves", "id": "valves_panel"},
            (2, 6): {"type": "lore", "lore_key": "veyr_fragment_1", "id": "frag1_lore"},
            (4, 4): {"type": "door", "requires_flag": "containment_stable", "id": "airlock_door"},
            (14, 6): {"type": "lift", "next_chapter": 4, "id": "lift_deck_09"}
        }
        return LevelData(3, grid, (1.5, 1.5, 0.0), 'lab', sprites, interactions)

    # ========================================================
    # CHAPTER 4: THE CORE VAULT
    # ========================================================
    @staticmethod
    def _build_chapter_4():
        grid = [
            "####################",
            "#P.....#...........#",
            "#.C1...#.....M.....#",
            "#......#...........#",
            "####D###############",
            "#......#.....#.....#",
            "#.C2...#..C3.#..E..#",
            "####################"
        ]
        sprites = [
            SpriteObject(2.5, 2.5, 'chip', entity_id='c1_sprite', interactive=True, label="[E] Security Terminal (Cipher 1)", is_objective=True),
            SpriteObject(2.5, 6.5, 'chip', entity_id='c2_sprite', interactive=True, label="[E] Damaged Terminal (Cipher 2)", is_objective=True),
            SpriteObject(10.5, 6.5, 'chip', entity_id='c3_sprite', interactive=True, label="[E] Captain's Terminal (Cipher 3)", is_objective=True)
        ]
        interactions = {
            (2, 2): {"type": "item", "item": "Cipher Fragment 1", "id": "cipher_1"},
            (13, 2): {"type": "puzzle", "puzzle_name": "defense_matrix", "id": "matrix_console"},
            (2, 6): {"type": "item", "item": "Cipher Fragment 2", "id": "cipher_2"},
            (10, 6): {"type": "item", "item": "Cipher Fragment 3", "id": "cipher_3"},
            (4, 4): {"type": "door", "requires_flag": "matrix_disabled", "id": "vault_bulkhead"},
            (16, 6): {"type": "lift", "next_chapter": 5, "id": "lift_deck_03"}
        }
        return LevelData(4, grid, (1.5, 1.5, 0.0), 'vault', sprites, interactions)

    # ========================================================
    # CHAPTER 5: WHISPERS IN THE DARK — OBSERVATION & COMMS
    # ========================================================
    @staticmethod
    def _build_chapter_5():
        grid = [
            "######################",
            "#P.....#.............#",
            "#.Z....#......A......#",
            "#......#.............#",
            "####D#################",
            "#......#......#......#",
            "#.S....#......#...E..#",
            "######################"
        ]
        sprites = [
            SpriteObject(2.5, 6.5, 'sera_hologram', entity_id='sera_holo_sprite', interactive=True, label="[E] Dr. Sera's Quantum Archive", is_objective=True)
        ]
        interactions = {
            (2, 2): {"type": "lore", "lore_key": "future_aegis_transmission", "id": "obs_void"},
            (14, 2): {"type": "puzzle", "puzzle_name": "transceiver_align", "id": "transceiver_panel"},
            (2, 6): {"type": "puzzle", "puzzle_name": "sera_harmonic", "id": "sera_sync_panel"},
            (4, 4): {"type": "door", "requires_flag": "distress_sent", "id": "comms_door"},
            (18, 6): {"type": "lift", "next_chapter": 6, "id": "lift_engine"}
        }
        return LevelData(5, grid, (1.5, 1.5, 0.0), 'comms', sprites, interactions)

    # ========================================================
    # CHAPTER 6: FINAL DIRECTIVE — CONTINUUM ENGINE CHAMBER
    # ========================================================
    @staticmethod
    def _build_chapter_6():
        grid = [
            "########################",
            "#P.....#...............#",
            "#......#.......W.......#",
            "#......#...............#",
            "####D###################",
            "#......#...M1..M2..M3..#",
            "#......#...............#",
            "#......#.......C.......#",
            "########################"
        ]
        sprites = [
            SpriteObject(15.5, 2.5, 'watcher_silhouette', entity_id='watcher_boss_sprite', interactive=True, label="[E] Speak with The Watcher", is_objective=True),
            SpriteObject(11.5, 5.5, 'projection', entity_id='proj_1_sprite', interactive=True, label="[E] Examine Colony Memory", is_objective=True),
            SpriteObject(15.5, 5.5, 'projection', entity_id='proj_2_sprite', interactive=True, label="[E] Examine Veyr City Memory", is_objective=True),
            SpriteObject(19.5, 5.5, 'projection', entity_id='proj_3_sprite', interactive=True, label="[E] Examine Peaceful Future Memory", is_objective=True)
        ]
        interactions = {
            (15, 2): {"type": "dialogue", "dialogue_id": "final_conversation", "id": "watcher_dialogue"},
            (11, 5): {"type": "lore", "lore_key": "veyr_fragment_1", "id": "proj_1"},
            (15, 5): {"type": "lore", "lore_key": "veyr_fragment_2", "id": "proj_2"},
            (19, 5): {"type": "lore", "lore_key": "veyr_fragment_3", "id": "proj_3"},
            (15, 7): {"type": "puzzle", "puzzle_name": "prime_directive", "id": "final_directive_console"},
            (4, 4): {"type": "door", "requires_flag": "final_approach", "id": "engine_door"}
        }
        return LevelData(6, grid, (1.5, 1.5, 0.0), 'engine', sprites, interactions)
