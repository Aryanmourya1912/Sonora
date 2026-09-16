import os
import random
from kivy.utils import platform

AndroidMediaPlayer = None

if platform == 'android':
    from jnius import PythonJavaClass, java_method, autoclass  # type: ignore

    class AndroidCompletionListener(PythonJavaClass):
        """Hardware callback that triggers immediately when a track ends."""
        __javainterfaces__ = ['android/media/MediaPlayer$OnCompletionListener']
        __javacontext__ = 'app'

        def __init__(self, callback):
            super().__init__()
            self.callback = callback

        @java_method('(Landroid/media/MediaPlayer;)V')
        def onCompletion(self, mp):
            if self.callback:
                self.callback()


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
    def __init__(self, on_complete_callback=None):
        self.queue = []
        self._unshuffled_queue = []
        self.current_index = -1
        self.is_playing = False
        self.is_paused = False
        self.repeat_mode = "off"  # "off" | "all" | "one"
        self.is_shuffled = False
        self.current_duration = 0.0
        self.seek_offset = 0.0
        self.on_complete_callback = on_complete_callback

        # Hardware handles
        self.android_player = None
        self.desktop_sound = None
        self._pause_pos = 0.0
        self._wake_lock = None
        self._completion_listener = None

    def _acquire_wake_lock(self):
        """Prevents Android from putting the CPU to sleep during downloads and playback."""
        if platform != 'android' or self._wake_lock:
            return
        try:
            from jnius import autoclass
            PythonActivity = autoclass('org.kivy.android.PythonActivity')
            PowerManager = autoclass('android.os.PowerManager')
            Context = autoclass('android.content.Context')

            activity = PythonActivity.mActivity
            if activity:
                pm = activity.getSystemService(Context.POWER_SERVICE)
                self._wake_lock = pm.newWakeLock(PowerManager.PARTIAL_WAKE_LOCK, "Sonora::AudioPlaybackLock")
                self._wake_lock.acquire()
        except Exception as e:
            print(f"[WakeLock Acquire Error] {e}")

    def _release_wake_lock(self):
        if self._wake_lock:
            try:
                if self._wake_lock.isHeld():
                    self._wake_lock.release()
            except Exception:
                pass
            self._wake_lock = None

    def load_queue(self, tracks: list, start_index: int = 0):
        self._unshuffled_queue = list(tracks)
        self.queue = list(tracks)
        self.current_index = max(0, min(start_index, len(self.queue) - 1)) if self.queue else -1

    def set_repeat_mode(self, mode: str):
        self.repeat_mode = mode

    def _get_player(self):
        if platform == 'android' and self.android_player is None:
            MP = get_android_media_player()
            if MP:
                try:
                    self.android_player = MP()
                    if self.on_complete_callback:
                        self._completion_listener = AndroidCompletionListener(self._handle_hardware_completion)
                        self.android_player.setOnCompletionListener(self._completion_listener)
                except Exception as e:
                    print(f"[Player Instantiation Error] {e}")
        return self.android_player

    def _handle_hardware_completion(self):
        if self.repeat_mode == "one":
            if self.android_player:
                self.android_player.seekTo(0)
                self.android_player.start()
            return

        if self.on_complete_callback:
            self.on_complete_callback()

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

        self._release_wake_lock()

    def play_local_file(self, file_path: str, duration: float = 0.0, start_pos: float = 0.0) -> bool:
        self.stop()
        self.current_duration = float(duration or 0.0)

        if not file_path or not os.path.exists(file_path):
            return False

        self._acquire_wake_lock()

        if platform == 'android':
            player = self._get_player()
            if not player:
                return False
            try:
                player.reset()

                # --- INSERTED: Tag stream as official Media/Music for Mini Capsule & Status Bar ---
                try:
                    from jnius import autoclass
                    AudioAttributes = autoclass('android.media.AudioAttributes')
                    AudioAttributesBuilder = autoclass('android.media.AudioAttributes$Builder')

                    attrs = AudioAttributesBuilder() \
                        .setUsage(AudioAttributes.USAGE_MEDIA) \
                        .setContentType(AudioAttributes.CONTENT_TYPE_MUSIC) \
                        .build()
                    player.setAudioAttributes(attrs)
                except Exception as attr_err:
                    print(f"[AudioAttributes Warning] {attr_err}")
                # ---------------------------------------------------------------------------------

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
                self._release_wake_lock()
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
                    self._release_wake_lock()
                elif self.is_paused:
                    self._acquire_wake_lock()
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