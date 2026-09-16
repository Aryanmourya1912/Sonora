import os
import random
from kivy.utils import platform

# Lazy-loaded Android MediaPlayer class handle
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
        self._unshuffled_queue = []
        self.current_index = -1
        self.is_playing = False
        self.is_paused = False
        self.repeat_mode = "off"  # "off" | "all" | "one"
        self.is_shuffled = False
        self.current_duration = 0.0
        self.seek_offset = 0.0

        # Hardware handles
        self.android_player = None
        self.desktop_sound = None
        self._pause_pos = 0.0

    def load_queue(self, tracks: list, start_index: int = 0):
        """Loads a song playlist into the active queue."""
        self._unshuffled_queue = list(tracks)
        self.queue = list(tracks)
        self.current_index = max(0, min(start_index, len(self.queue) - 1)) if self.queue else -1

    def set_repeat_mode(self, mode: str):
        """Sets repeat mode: 'off', 'all', or 'one'."""
        self.repeat_mode = mode

    def _get_player(self):
        """Instantiates Android MediaPlayer on demand."""
        if platform == 'android' and self.android_player is None:
            MP = get_android_media_player()
            if MP:
                try:
                    self.android_player = MP()
                except Exception as e:
                    print(f"[Player Instantiation Error] {e}")
        return self.android_player

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
            player = self._get_player()
            if not player:
                return False
            try:
                # 1. Reset state before setting new data source
                player.reset()

                # 2. Prevent CPU sleep while music plays in background
                try:
                    from jnius import autoclass  # type: ignore

                    PythonActivity = autoclass('org.kivy.android.PythonActivity')
                    PowerManager = autoclass('android.os.PowerManager')
                    
                    activity = PythonActivity.mActivity
                    if activity:
                        context = activity.getApplicationContext()
                        player.setWakeMode(context, PowerManager.PARTIAL_WAKE_LOCK)
                except Exception as wake_err:
                    print(f"[WakeLock Warning] {wake_err}")

                # 3. Load audio file and prepare
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
            except Exception as err:
                print(f"[Android Media Play Error] {err}")
                self.is_playing = False
                return False
        else:
            try:
                from kivy.core.audio import SoundLoader
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
                print(f"[Desktop Media Play Error] {err}")
                self.is_playing = False
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
                if not self.is_playing and not self.is_paused:
                    self.android_player.start()
                    self.is_playing = True
            except Exception:
                pass
        elif self.desktop_sound:
            try:
                self.desktop_sound.seek(target_sec)
                self._pause_pos = target_sec
            except Exception:
                pass

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
        """Determines if the active track completed, guarding against startup buffering false-positives."""
        if not self.is_playing or self.is_paused:
            return False

        if platform == 'android' and self.android_player:
            try:
                pos, dur = self.get_progress()
                # Guard: Do not mark finished if song just started buffering (< 1.5s)
                if pos < 1.5:
                    return False
                return not self.android_player.isPlaying() and (pos >= dur - 2.0)
            except Exception:
                return False
        elif self.desktop_sound:
            return self.desktop_sound.state == 'stop'
        return False