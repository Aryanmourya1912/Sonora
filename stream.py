import os
import random
from kivy.core.audio import SoundLoader

class AudioController:
    def __init__(self):
        self.queue = []
        self.current_index = -1
        self.is_playing = False
        self.is_paused = False
        self.repeat_mode = "off"  # "off" | "one" | "all"
        self.is_shuffled = False
        self._unshuffled_queue = []
        self.current_duration = 0.0
        self.sound = None
        self._pause_pos = 0.0

    def load_queue(self, tracks: list[dict], start_index: int = 0):
        self._unshuffled_queue = list(tracks)
        self.queue = list(tracks)
        self.current_index = start_index

    def stop(self):
        self.is_playing = False
        self.is_paused = False
        self._pause_pos = 0.0
        if self.sound:
            try:
                self.sound.stop()
                self.sound.unload()
            except Exception:
                pass
            self.sound = None

    def play_local_file(self, file_path: str, duration: float = 0.0, start_pos: float = 0.0) -> bool:
        self.stop()
        self.current_duration = float(duration or 0.0)

        if not file_path or not os.path.exists(file_path):
            return False

        try:
            self.sound = SoundLoader.load(file_path)
            if not self.sound:
                return False

            if self.current_duration <= 0 and hasattr(self.sound, 'length') and self.sound.length > 0:
                self.current_duration = float(self.sound.length)

            self.sound.play()
            if start_pos > 0:
                self.sound.seek(start_pos)
                self._pause_pos = start_pos

            self.is_playing = True
            self.is_paused = False
            return True
        except Exception as e:
            print(f"[Audio Error] {e}")

        self.is_playing = False
        return False

    def toggle_play_pause(self):
        if not self.sound:
            return

        if self.is_playing:
            try:
                self._pause_pos = self.sound.get_pos()
                self.sound.stop()
            except Exception:
                pass
            self.is_playing = False
            self.is_paused = True
        elif self.is_paused:
            try:
                self.sound.play()
                if self._pause_pos > 0:
                    self.sound.seek(self._pause_pos)
            except Exception:
                pass
            self.is_playing = True
            self.is_paused = False

    def seek(self, position_ratio: float):
        if not self.sound or self.current_duration <= 0:
            return

        target_pos = self.current_duration * max(0.0, min(1.0, position_ratio))
        try:
            self.sound.seek(target_pos)
            self._pause_pos = target_pos
            if not self.is_playing:
                self.sound.play()
                self.is_playing = True
                self.is_paused = False
        except Exception as e:
            print(f"[Seek Error] {e}")

    def toggle_shuffle(self):
        self.is_shuffled = not self.is_shuffled
        if self.is_shuffled:
            current_track = self.queue[self.current_index] if (0 <= self.current_index < len(self.queue)) else None
            random.shuffle(self.queue)
            if current_track in self.queue:
                self.queue.remove(current_track)
                self.queue.insert(0, current_track)
                self.current_index = 0
        else:
            current_track = self.queue[self.current_index] if (0 <= self.current_index < len(self.queue)) else None
            self.queue = list(self._unshuffled_queue)
            if current_track in self.queue:
                self.current_index = self.queue.index(current_track)

    def set_repeat_mode(self, mode: str):
        self.repeat_mode = mode

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

    def get_progress(self) -> tuple[float, float]:
        if not self.sound or (not self.is_playing and not self.is_paused):
            return 0.0, max(self.current_duration, 1.0)

        pos = 0.0
        try:
            if self.is_paused:
                pos = self._pause_pos
            else:
                pos = self.sound.get_pos() or 0.0
        except Exception:
            pass

        dur = max(self.current_duration, getattr(self.sound, 'length', 0.0) or 0.0, 1.0)
        return max(0.0, min(pos, dur)), dur

    def is_finished(self) -> bool:
        if self.is_playing and self.sound:
            return self.sound.state == 'stop'
        return False