import os
import random
from kivy.utils import platform

if platform == 'android':
    from jnius import autoclass
    AndroidMediaPlayer = autoclass('android.media.MediaPlayer')
else:
    from kivy.core.audio import SoundLoader
    AndroidMediaPlayer = None

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

        # Engine handles
        self.android_player = AndroidMediaPlayer() if AndroidMediaPlayer else None
        self.desktop_sound = None
        self._pause_pos = 0.0

    def load_queue(self, tracks: list[dict], start_index: int = 0):
        self._unshuffled_queue = list(tracks)
        self.queue = list(tracks)
        self.current_index = start_index

    def stop(self):
        self.is_playing = False
        self.is_paused = False
        self._pause_pos = 0.0

        if platform == 'android' and self.android_player:
            try:
                if self.android_player.isPlaying():
                    self.android_player.stop()
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

    def play_local_file(self, file_path: str, duration: float = 0.0, start_pos: float = 0.0) -> bool:
        self.stop()
        self.current_duration = float(duration or 0.0)

        if not file_path or not os.path.exists(file_path):
            return False

        if platform == 'android':
            try:
                self.android_player.reset()
                self.android_player.setDataSource(file_path)
                self.android_player.prepare()
                
                if start_pos > 0:
                    self.android_player.seekTo(int(start_pos * 1000))
                
                self.android_player.start()
                self.is_playing = True
                self.is_paused = False

                dur_ms = self.android_player.getDuration()
                if dur_ms > 0:
                    self.current_duration = float(dur_ms) / 1000.0
                return True
            except Exception as err:
                print(f"[Android Media Error] {err}")
                return False
        else:
            try:
                self.desktop_sound = SoundLoader.load(file_path)
                if not self.desktop_sound:
                    return False
                self.desktop_sound.play()
                if start_pos > 0:
                    self.desktop_sound.seek(start_pos)
                self.is_playing = True
                self.is_paused = False
                return True
            except Exception as err:
                print(f"[Desktop Media Error] {err}")
                return False

    def toggle_play_pause(self):
        if platform == 'android' and self.android_player:
            try:
                if self.is_playing:
                    self.android_player.pause()
                    self.is_playing = False
                    self.is_paused = True
                elif self.is_paused:
                    self.android_player.start()
                    self.is_playing = True
                    self.is_paused = False
            except Exception:
                pass
        elif self.desktop_sound:
            if self.is_playing:
                self._pause_pos = self.desktop_sound.get_pos()
                self.desktop_sound.stop()
                self.is_playing = False
                self.is_paused = True
            elif self.is_paused:
                self.desktop_sound.play()
                if self._pause_pos > 0:
                    self.desktop_sound.seek(self._pause_pos)
                self.is_playing = True
                self.is_paused = False

    def seek(self, position_ratio: float):
        if self.current_duration <= 0:
            return
        target_sec = self.current_duration * max(0.0, min(1.0, position_ratio))

        if platform == 'android' and self.android_player:
            try:
                self.android_player.seekTo(int(target_sec * 1000))
                if not self.is_playing:
                    self.android_player.start()
                    self.is_playing = True
                    self.is_paused = False
            except Exception:
                pass
        elif self.desktop_sound:
            try:
                self.desktop_sound.seek(target_sec)
                self._pause_pos = target_sec
            except Exception:
                pass

    def get_progress(self) -> tuple[float, float]:
        dur = max(self.current_duration, 1.0)
        pos = 0.0

        if platform == 'android' and self.android_player:
            try:
                pos = float(self.android_player.getCurrentPosition()) / 1000.0
            except Exception:
                pos = 0.0
        elif self.desktop_sound:
            try:
                pos = self._pause_pos if self.is_paused else (self.desktop_sound.get_pos() or 0.0)
            except Exception:
                pos = 0.0

        return max(0.0, min(pos, dur)), dur

    def is_finished(self) -> bool:
        if platform == 'android' and self.android_player:
            try:
                return not self.android_player.isPlaying() and not self.is_paused and self.is_playing
            except Exception:
                return False
        elif self.desktop_sound and self.is_playing:
            return self.desktop_sound.state == 'stop'
        return False

    def next_track(self) -> dict | None:
        if not self.queue:
            return None
        if self.repeat_mode == "one":
            return self.queue[self.current_index]
        if self.current_index + 1 < len(self.queue):
            self.current_index += 1
            return self.queue[self.current_index]
        elif self.repeat_mode == "all":
            self.current_index = 0
            return self.queue[0]
        return None

    def prev_track(self) -> dict | None:
        if not self.queue:
            return None
        if self.current_index > 0:
            self.current_index -= 1
            return self.queue[self.current_index]
        return self.queue[0]