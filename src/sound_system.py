import pygame
import numpy as np
import math

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
        self.volume = 0.7
        self.voice_volume = 0.5
        self.sample_rate = 22050

        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init(frequency=self.sample_rate, size=-16, channels=2, buffer=512)
            self.enabled = True
            self._generate_procedural_sounds()
        except Exception as e:
            print(f"[SoundSystem] Audio init fallback (running silent): {e}")
            self.enabled = False

    def _make_sound(self, arr):
        """Converts float numpy array (-1.0 to 1.0) into stereo Pygame Sound."""
        arr = np.clip(arr, -1.0, 1.0)
        int_arr = (arr * 32767).astype(np.int16)
        stereo_arr = np.column_stack((int_arr, int_arr))
        return pygame.sndarray.make_sound(stereo_arr)

    def _generate_procedural_sounds(self):
        sr = self.sample_rate

        # 1. Beep / UI Click
        t = np.linspace(0, 0.05, int(sr * 0.05), False)
        beep = np.sin(2 * np.pi * 880 * t) * np.exp(-t * 40)
        self.sounds['ui_beep'] = self._make_sound(beep)

        # 2. Access Granted
        t = np.linspace(0, 0.25, int(sr * 0.25), False)
        chord = (np.sin(2 * np.pi * 523.25 * t) + np.sin(2 * np.pi * 659.25 * t) + np.sin(2 * np.pi * 783.99 * t)) / 3.0
        chord *= np.exp(-t * 8)
        self.sounds['access_granted'] = self._make_sound(chord)

        # 3. Access Denied / Warning
        t = np.linspace(0, 0.3, int(sr * 0.3), False)
        buzz = (np.sin(2 * np.pi * 150 * t) + 0.5 * np.sin(2 * np.pi * 210 * t)) * np.exp(-t * 6)
        self.sounds['access_denied'] = self._make_sound(buzz)

        # 4. Radio Burst / Static
        t = np.linspace(0, 0.12, int(sr * 0.12), False)
        noise = (np.random.rand(len(t)) * 2 - 1) * np.exp(-t * 15)
        tone = np.sin(2 * np.pi * 1200 * t) * 0.3
        self.sounds['radio_burst'] = self._make_sound(noise + tone)

        # 5. Flashlight Click
        t = np.linspace(0, 0.03, int(sr * 0.03), False)
        click = (np.random.rand(len(t)) * 2 - 1) * np.exp(-t * 80)
        self.sounds['flashlight'] = self._make_sound(click)

        # 6. Footstep on metal
        t = np.linspace(0, 0.08, int(sr * 0.08), False)
        thud = np.sin(2 * np.pi * 90 * t) * np.exp(-t * 45) + (np.random.rand(len(t)) * 0.2 - 0.1) * np.exp(-t * 30)
        self.sounds['footstep'] = self._make_sound(thud)

        # 7. Drone Alert Ping
        t = np.linspace(0, 0.35, int(sr * 0.35), False)
        f_sweep = np.linspace(600, 1400, len(t))
        sweep = np.sin(2 * np.pi * f_sweep * t) * np.exp(-t * 4)
        self.sounds['drone_alert'] = self._make_sound(sweep)

        # 8. Alien Harmonic Hum
        t = np.linspace(0, 1.2, int(sr * 1.2), False)
        harm = (np.sin(2 * np.pi * 220 * t) + np.sin(2 * np.pi * 330 * t) * 0.7 + np.sin(2 * np.pi * 440 * t) * 0.5 + np.sin(2 * np.pi * 550 * t) * 0.3) / 2.5
        harm *= np.sin(np.pi * t / 1.2)  # Fade in and out
        self.sounds['alien_hum'] = self._make_sound(harm)

        # 9. Electrical Spark / Arc
        t = np.linspace(0, 0.15, int(sr * 0.15), False)
        spark = (np.random.rand(len(t)) * 2 - 1) * (np.sin(2 * np.pi * 300 * t) > 0.5) * np.exp(-t * 10)
        self.sounds['spark'] = self._make_sound(spark)

        # 10. Voice blips
        chars = {
            'clara': 380,
            'ward': 180,
            'nova': 580,
            'malik': 260,
            'watcher': 110,
            'sera': 520,
            'default': 440
        }
        for name, freq in chars.items():
            t_v = np.linspace(0, 0.035, int(sr * 0.035), False)
            if name == 'watcher':
                # Deep square-ish sub-bass
                v_blip = np.sign(np.sin(2 * np.pi * freq * t_v)) * 0.4 * np.exp(-t_v * 25)
            elif name == 'nova':
                # Pure clear sine wave
                v_blip = np.sin(2 * np.pi * freq * t_v) * 0.4 * np.exp(-t_v * 30)
            else:
                # Triangle/rich wave
                v_blip = (np.sin(2 * np.pi * freq * t_v) + 0.3 * np.sin(2 * np.pi * (freq * 2) * t_v)) * 0.35 * np.exp(-t_v * 25)
            self.sounds[f'voice_{name}'] = self._make_sound(v_blip)

    def play(self, sound_name, volume=None):
        if not self.enabled: return
        snd = self.sounds.get(sound_name)
        if snd:
            vol = volume if volume is not None else self.volume
            snd.set_volume(vol)
            snd.play()

    def play_voice(self, speaker_name):
        if not self.enabled: return
        key = speaker_name.lower()
        matched = 'default'
        for k in ['clara', 'ward', 'nova', 'malik', 'watcher', 'sera']:
            if k in key:
                matched = k
                break
        self.play(f'voice_{matched}', volume=self.voice_volume)
