import os
import random
import pygame

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
        self.seek_offset = 0.0

        try:
            pygame.mixer.pre_init(44100, -16, 2, 2048)
            pygame.mixer.init()
        except Exception as e:
            print(f"[Pygame Audio Init Error] {e}")

    def load_queue(self, tracks: list[dict], start_index: int = 0):
        self._unshuffled_queue = list(tracks)
        self.queue = list(tracks)
        self.current_index = start_index

    def stop(self):
        self.is_playing = False
        self.is_paused = False
        self.seek_offset = 0.0
        try:
            pygame.mixer.music.stop()
            if hasattr(pygame.mixer.music, 'unload'):
                pygame.mixer.music.unload()
        except Exception:
            pass

    def play_local_file(self, file_path: str, duration: float = 0.0, start_pos: float = 0.0) -> bool:
        self.current_duration = float(duration or 0.0)
        self.stop()

        if not file_path or not os.path.exists(file_path):
            return False

        try:
            pygame.mixer.music.load(file_path)
            if start_pos > 0.0:
                pygame.mixer.music.play(start=start_pos)
                self.seek_offset = start_pos
            else:
                pygame.mixer.music.play()
                self.seek_offset = 0.0

            self.is_playing = True
            self.is_paused = False
            return True
        except Exception as e:
            print(f"[Audio Error] {e}")

        self.is_playing = False
        return False

    def toggle_play_pause(self):
        if not self.is_playing and not self.is_paused:
            return

        if self.is_playing:
            try:
                pygame.mixer.music.pause()
            except Exception:
                pass
            self.is_playing = False
            self.is_paused = True
        else:
            try:
                pygame.mixer.music.unpause()
            except Exception:
                pass
            self.is_playing = True
            self.is_paused = False

    def seek(self, position_ratio: float):
        if self.current_duration <= 0:
            return

        target_pos = self.current_duration * max(0.0, min(1.0, position_ratio))
        try:
            pygame.mixer.music.play(start=target_pos)
            self.seek_offset = target_pos
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
        if not self.is_playing and not self.is_paused:
            return 0.0, max(self.current_duration, 1.0)

        elapsed_ms = pygame.mixer.music.get_pos()
        if elapsed_ms < 0:
            elapsed_ms = 0

        pos = self.seek_offset + (elapsed_ms / 1000.0)
        if self.current_duration > 0:
            pos = min(self.current_duration, pos)

        return max(0.0, pos), max(self.current_duration, 1.0)

    def is_finished(self) -> bool:
        if self.is_playing and not self.is_paused:
            return not pygame.mixer.music.get_busy()
        return False