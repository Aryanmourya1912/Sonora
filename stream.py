import os
import random
from kivy.utils import platform

# DO NOT call autoclass here at module root!
AndroidMediaPlayer = None

def get_android_media_player():
    global AndroidMediaPlayer
    if platform == 'android' and AndroidMediaPlayer is None:
        try:
            from jnius import autoclass
            AndroidMediaPlayer = autoclass('android.media.MediaPlayer')
        except Exception as e:
            print(f"[JNI Load Error] {e}")
    return AndroidMediaPlayer


class AudioController:
    def __init__(self):
        self.queue = []
        self.current_index = -1
        self.is_playing = False
        self.is_paused = False
        self.repeat_mode = "off"
        self.is_shuffled = False
        self._unshuffled_queue = []
        self.current_duration = 0.0

        self.android_player = None
        self.desktop_sound = None
        self._pause_pos = 0.0

    def _get_player(self):
        if platform == 'android' and self.android_player is None:
            MP = get_android_media_player()
            if MP:
                try:
                    self.android_player = MP()
                except Exception as e:
                    print(f"[Player Instantiation Error] {e}")
        return self.android_player

    def play_local_file(self, file_path: str, duration: float = 0.0, start_pos: float = 0.0) -> bool:
        self.stop()
        self.current_duration = float(duration or 0.0)

        if not file_path or not os.path.exists(file_path):
            return False

        if platform == 'android':
            player = self._get_player()
            if not player:
                return False
            try:
                player.reset()
                player.setDataSource(file_path)
                player.prepare()
                if start_pos > 0:
                    player.seekTo(int(start_pos * 1000))
                player.start()
                self.is_playing = True
                self.is_paused = False
                dur_ms = player.getDuration()
                if dur_ms > 0:
                    self.current_duration = float(dur_ms) / 1000.0
                return True
            except Exception as e:
                print(f"[Playback Error] {e}")
                return False
        else:
            from kivy.core.audio import SoundLoader
            self.desktop_sound = SoundLoader.load(file_path)
            if self.desktop_sound:
                self.desktop_sound.play()
                if start_pos > 0:
                    self.desktop_sound.seek(start_pos)
                self.is_playing = True
                self.is_paused = False
                return True
            return False

    def stop(self):
        self.is_playing = False
        self.is_paused = False
        self._pause_pos = 0.0
        if platform == 'android' and self.android_player:
            try:
                self.android_player.reset()
            except Exception:
                pass
        elif self.desktop_sound:
            try:
                self.desktop_sound.stop()
                self.desktop_sound.unload()
            except Exception:
                pass
            self.desktop_sound = None