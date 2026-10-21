import os
import pygame
import numpy as np
import math
from src.config import BUNDLE_DIR, BASE_DIR

class SoundSystem:
    _instance = None

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = SoundSystem()
        return cls._instance

    def __init__(self):
        self.enabled = False
        self.sounds = {}
        self.voice_clips = {}
        self.volume = 0.75
        self.voice_volume = 0.90
        self.ambient_volume = 0.35
        self.sample_rate = 44100
        self.step_toggle = False
        self.ambient_channel = None
        self.voice_channel = None

        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init(frequency=self.sample_rate, size=-16, channels=2, buffer=1024)
            pygame.mixer.set_num_channels(16)
            self.ambient_channel = pygame.mixer.Channel(0)
            self.voice_channel = pygame.mixer.Channel(1)
            self.enabled = True
            self._load_audio_files()
            self._generate_procedural_fallbacks()
        except Exception as e:
            print(f"[SoundSystem] Audio init warning (running fallback/silent): {e}")
            self.enabled = False

    def _get_audio_dir(self, subdir):
        for base in [BUNDLE_DIR, BASE_DIR, os.path.dirname(os.path.dirname(os.path.abspath(__file__)))]:
            candidate = os.path.join(base, "assets", "audio", subdir)
            if os.path.exists(candidate):
                return candidate
        return None

    def _load_audio_files(self):
        # 1. Load SFX
        sfx_dir = self._get_audio_dir("sfx")
        if sfx_dir and os.path.exists(sfx_dir):
            for f in os.listdir(sfx_dir):
                if f.lower().endswith(('.wav', '.ogg')):
                    name = os.path.splitext(f)[0]
                    try:
                        self.sounds[name] = pygame.mixer.Sound(os.path.join(sfx_dir, f))
                    except Exception as e:
                        print(f"[SoundSystem] Error loading sfx {f}: {e}")

        # 2. Load Voices
        voices_dir = self._get_audio_dir("voices")
        if voices_dir and os.path.exists(voices_dir):
            for f in os.listdir(voices_dir):
                if f.lower().endswith(('.wav', '.ogg')):
                    name = os.path.splitext(f)[0]
                    try:
                        self.voice_clips[name] = pygame.mixer.Sound(os.path.join(voices_dir, f))
                    except Exception as e:
                        print(f"[SoundSystem] Error loading voice clip {f}: {e}")

    def _make_sound(self, arr):
        """Converts float numpy array (-1.0 to 1.0) into stereo Pygame Sound."""
        arr = np.clip(arr, -1.0, 1.0)
        int_arr = (arr * 32767).astype(np.int16)
        stereo_arr = np.column_stack((int_arr, int_arr))
        return pygame.sndarray.make_sound(stereo_arr)

    def _generate_procedural_fallbacks(self):
        sr = 22050
        # Beep fallback
        if 'terminal_chirp' not in self.sounds and 'ui_beep' not in self.sounds:
            t = np.linspace(0, 0.05, int(sr * 0.05), False)
            beep = np.sin(2 * np.pi * 880 * t) * np.exp(-t * 40)
            self.sounds['ui_beep'] = self._make_sound(beep)

        # Access granted fallback
        if 'scan_success' not in self.sounds and 'access_granted' not in self.sounds:
            t = np.linspace(0, 0.25, int(sr * 0.25), False)
            chord = (np.sin(2 * np.pi * 523.25 * t) + np.sin(2 * np.pi * 659.25 * t)) / 2.0
            self.sounds['access_granted'] = self._make_sound(chord * np.exp(-t * 8))

        # Access denied fallback
        if 'scan_denied' not in self.sounds and 'access_denied' not in self.sounds:
            t = np.linspace(0, 0.3, int(sr * 0.3), False)
            buzz = np.sin(2 * np.pi * 150 * t) * np.exp(-t * 6)
            self.sounds['access_denied'] = self._make_sound(buzz)

        # Radio Burst fallback
        if 'radio_burst' not in self.sounds:
            t = np.linspace(0, 0.12, int(sr * 0.12), False)
            noise = (np.random.rand(len(t)) * 2 - 1) * np.exp(-t * 15)
            self.sounds['radio_burst'] = self._make_sound(noise)

        # Footstep fallback
        if 'footstep_metal_1' not in self.sounds:
            t = np.linspace(0, 0.08, int(sr * 0.08), False)
            thud = np.sin(2 * np.pi * 90 * t) * np.exp(-t * 45)
            self.sounds['footstep'] = self._make_sound(thud)

        # Pneumatic door slide (open): air hiss + rising servo whine
        if 'door_blast_open' not in self.sounds and 'door_open' not in self.sounds:
            t = np.linspace(0, 0.55, int(sr * 0.55), False)
            hiss = (np.random.rand(len(t)) * 2 - 1) * 0.35 * np.sin(np.pi * t / 0.55)
            servo = np.sin(2 * np.pi * (180 + 260 * t) * t) * 0.25 * np.sin(np.pi * t / 0.55)
            self.sounds['door_open'] = self._make_sound(hiss + servo)

        # Door seal (close): servo whine down + heavy latch thud
        if 'door_blast_close' not in self.sounds and 'door_close' not in self.sounds:
            t = np.linspace(0, 0.5, int(sr * 0.5), False)
            servo = np.sin(2 * np.pi * (420 - 300 * t) * t) * 0.22 * np.exp(-t * 3)
            since_latch = np.clip(t - 0.3, 0.0, None)
            thud = np.sin(2 * np.pi * 70 * t) * np.exp(-since_latch * 18) * (t > 0.3) * 0.9
            self.sounds['door_close'] = self._make_sound(servo + thud)

        # Voice chatter blips
        chars = {'clara': 380, 'ward': 180, 'nova': 580, 'malik': 260, 'watcher': 110, 'default': 440}
        for name, freq in chars.items():
            t_v = np.linspace(0, 0.035, int(sr * 0.035), False)
            v_blip = np.sin(2 * np.pi * freq * t_v) * 0.35 * np.exp(-t_v * 25)
            self.sounds[f'voice_{name}'] = self._make_sound(v_blip)

    def play(self, sound_name, volume=None):
        if not self.enabled: return

        # Smart alias routing to realistic SFX
        mapped_name = sound_name
        if sound_name == 'footstep':
            self.step_toggle = not self.step_toggle
            mapped_name = 'footstep_metal_1' if self.step_toggle else 'footstep_metal_2'
            if mapped_name not in self.sounds: mapped_name = 'footstep'
        elif sound_name == 'ui_beep':
            if 'terminal_chirp' in self.sounds: mapped_name = 'terminal_chirp'
        elif sound_name == 'access_granted':
            if 'scan_success' in self.sounds: mapped_name = 'scan_success'
        elif sound_name == 'access_denied':
            if 'scan_denied' in self.sounds: mapped_name = 'scan_denied'
        elif sound_name == 'spark':
            if 'electric_arc' in self.sounds: mapped_name = 'electric_arc'
        elif sound_name in ['door_open', 'door_unlock']:
            if 'door_blast_open' in self.sounds: mapped_name = 'door_blast_open'
        elif sound_name in ['door_close', 'door_lock']:
            if 'door_blast_close' in self.sounds: mapped_name = 'door_blast_close'

        snd = self.sounds.get(mapped_name, self.sounds.get(sound_name))
        if snd:
            vol = volume if volume is not None else self.volume
            snd.set_volume(vol)
            snd.play()

    def play_voice_clip(self, clip_name, volume=None):
        """Plays full human/AI voiceover track on dedicated voice channel."""
        if not self.enabled: return False
        clip = self.voice_clips.get(clip_name)
        if clip:
            vol = volume if volume is not None else self.voice_volume
            clip.set_volume(vol)
            if self.voice_channel:
                self.voice_channel.stop()
                self.voice_channel.play(clip)
            else:
                clip.play()
            return True
        return False

    def is_voice_playing(self):
        if not self.enabled or not self.voice_channel:
            return False
        return self.voice_channel.get_busy()

    def start_ambient(self, track_name='ambient_dreadnought_hum', volume=None):
        """Plays looping ambient reactor background hum."""
        if not self.enabled or not self.ambient_channel: return
        snd = self.sounds.get(track_name)
        if snd:
            vol = volume if volume is not None else self.ambient_volume
            snd.set_volume(vol)
            self.ambient_channel.play(snd, loops=-1)

    def stop_ambient(self):
        if self.enabled and self.ambient_channel:
            self.ambient_channel.stop()

    def play_voice(self, speaker_name):
        if not self.enabled: return
        # If full voiceover is playing, don't spam radio blips over speech
        if self.is_voice_playing():
            return
        key = speaker_name.lower()
        matched = 'default'
        for k in ['clara', 'ward', 'nova', 'malik', 'watcher', 'sera']:
            if k in key:
                matched = k
                break
        self.play(f'voice_{matched}', volume=0.35)
