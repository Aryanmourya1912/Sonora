import os
import sys
from datetime import datetime

# 1. Image and SSL Environment Fixes
os.environ['KIVY_IMAGE'] = 'pil,sdl2'
try:
    import certifi
    os.environ['SSL_CERT_FILE'] = certifi.where()
    os.environ['SSL_CERT_DIR'] = os.path.dirname(certifi.where())
except Exception:
    pass

import logging
import urllib.request
import threading
import mutagen
import traceback

logging.getLogger("PIL").setLevel(logging.WARNING)

from kivy.utils import platform
from kivy.core.window import Window

# Lock orientation sizing only for desktop testing
if platform != 'android':
    Window.size = (420, 760)

from kivymd.app import MDApp
from kivymd.uix.label import MDLabel
from kivymd.uix.list import (
    TwoLineAvatarIconListItem,
    OneLineIconListItem,
    OneLineListItem,
    IconLeftWidget,
    IconRightWidget
)
from kivymd.uix.button import MDFlatButton, MDRaisedButton
from kivy.uix.button import Button
from kivymd.uix.dialog import MDDialog
from kivymd.uix.boxlayout import MDBoxLayout
from kivy.uix.boxlayout import BoxLayout
from kivymd.uix.scrollview import MDScrollView
from kivymd.uix.list import MDList
from kivymd.uix.menu import MDDropdownMenu
from kivy.core.clipboard import Clipboard
from kivy.metrics import dp
from kivy.clock import Clock
from kivy.animation import Animation
from kivy.app import App
from kivy.uix.scrollview import ScrollView
from kivy.uix.label import Label
from kivy.uix.modalview import ModalView
from kivy.uix.textinput import TextInput

from search import SearchEngine
from stream import AudioController
from playlist import PlaylistManager
from download import Downloader
from ui import PlayerScreen, SongCard
from notification_helper import PlaybackNotificationManager


def format_time(seconds: float) -> str:
    seconds = max(0, int(seconds))
    mins, secs = divmod(seconds, 60)
    hours, mins = divmod(mins, 60)
    if hours > 0:
        return f"{hours}:{mins:02d}:{secs:02d}"
    return f"{mins}:{secs:02d}"


# ==========================================
# Global Background Thread Crash Handler
# ==========================================
def display_thread_crash(error_text: str):
    """Displays a scrollable, copyable crash pop-up over the active screen."""
    popup = ModalView(size_hint=(0.92, 0.85), auto_dismiss=True)
    box = TextInput(
        text=f"--- THREAD RUNTIME ERROR ---\n\n{error_text}",
        readonly=True,
        font_size="12sp",
        background_color=(0.1, 0.1, 0.1, 0.95),
        foreground_color=(1.0, 0.4, 0.4, 1),
        size_hint=(1, 1),
        padding=[15, 20, 15, 15],
    )
    popup.add_widget(box)
    popup.open()


def write_crash_log(error_text: str):
    """Appends crash tracebacks to crash.log inside user_data_dir."""
    try:
        app = MDApp.get_running_app()
        if app and hasattr(app, 'user_data_dir') and app.user_data_dir:
            base_dir = app.user_data_dir
        else:
            base_dir = os.path.dirname(os.path.abspath(__file__))

        log_path = os.path.join(base_dir, "crash.log")
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        with open(log_path, "a", encoding="utf-8") as f:
            f.write(f"\n{'='*50}\n[{timestamp}]\n{error_text}\n{'='*50}\n")
    except Exception as log_err:
        print(f"[Crash File Logger Failed] {log_err}")


def global_thread_exception_handler(args):
    """Intercepts unhandled exceptions across all background threads."""
    err_msg = "".join(
        traceback.format_exception(
            args.exc_type, args.exc_value, args.exc_traceback
        )
    )
    thread_name = getattr(args.thread, "name", "Unknown Thread")
    full_log = f"Thread: {thread_name}\n\n{err_msg}"

    print(f"[Thread Crash Intercepted] {full_log}")

    # 1. Write traceback offline to phone storage
    write_crash_log(full_log)

    # 2. Render visually on the phone screen
    Clock.schedule_once(lambda dt: display_thread_crash(full_log), 0)


# Bind hook at startup
threading.excepthook = global_thread_exception_handler


# ==========================================
# Main Application Class
# ==========================================
class MusicPlayerApp(MDApp):

    def _get_cache_dir(self) -> str:
        """Returns a guaranteed writable storage folder for artwork."""
        cache_path = os.path.join(self.user_data_dir, "thumbs")
        os.makedirs(cache_path, exist_ok=True)
        return cache_path

    def open_crash_log_viewer(self):
        """Opens a modal dialog showing recorded crash logs with an option to wipe them."""
        log_path = os.path.join(self.user_data_dir, "crash.log")

        content_text = "No crash logs recorded yet."
        if os.path.exists(log_path):
            try:
                with open(log_path, "r", encoding="utf-8") as f:
                    content = f.read().strip()
                    content_text = content if content else "crash.log is currently empty."
            except Exception as read_err:
                content_text = f"Failed to read crash log: {read_err}"

        modal = ModalView(size_hint=(0.92, 0.85), auto_dismiss=True)
        container = BoxLayout(orientation="vertical", spacing=10, padding=12)

        text_box = TextInput(
            text=content_text,
            readonly=True,
            font_size="12sp",
            background_color=(0.10, 0.10, 0.10, 1),
            foreground_color=(0.95, 0.95, 0.95, 1),
            size_hint=(1, 0.88),
            padding=[12, 12, 12, 12],
        )

        btn_bar = BoxLayout(orientation="horizontal", size_hint=(1, 0.12), spacing=10)

        def _clear_logs(instance):
            try:
                if os.path.exists(log_path):
                    os.remove(log_path)
                text_box.text = "crash.log cleared successfully."
            except Exception as del_err:
                text_box.text = f"Failed to delete crash log: {del_err}"

        btn_clear = Button(
            text="Clear Logs",
            background_color=(0.85, 0.25, 0.25, 1),
            size_hint=(0.5, 1),
        )
        btn_clear.bind(on_release=_clear_logs)

        btn_close = Button(
            text="Close",
            background_color=(0.25, 0.25, 0.25, 1),
            size_hint=(0.5, 1),
        )
        btn_close.bind(on_release=modal.dismiss)

        btn_bar.add_widget(btn_clear)
        btn_bar.add_widget(btn_close)

        container.add_widget(text_box)
        container.add_widget(btn_bar)
        modal.add_widget(container)

        modal.open()

    def _trigger_menu_action(self, action_func):
        """Dismisses the dropdown menu safely before executing an action."""
        menu = getattr(self, 'menu', None)
        if menu:
            menu.dismiss()
        action_func()

    def _build_crash_screen(self, error_trace: str):
        """Displays full traceback in a high-contrast, copyable text box."""
        write_crash_log(f"Main Thread Startup Crash:\n\n{error_trace}")

        return TextInput(
            text=f"--- RUNTIME CRASH DETECTED ---\n\n{error_trace}",
            readonly=True,
            font_size="13sp",
            background_color=(0.08, 0.08, 0.08, 1),
            foreground_color=(1.0, 0.35, 0.35, 1),
            size_hint=(1, 1),
            padding=[20, 40, 20, 20],
        )

    def build(self):
        try:
            return self._safe_build()
        except Exception:
            return self._build_crash_screen(traceback.format_exc())

    def _safe_build(self):
        self.theme_cls.theme_style = "Dark"
        self.theme_cls.primary_palette = "Amber"

        self.search_engine = SearchEngine()
        self.audio = AudioController()
        self.playlist_mgr = PlaylistManager()
        self.downloader = Downloader()

        self.current_track = None
        self.active_tab = "home"
        self._current_fetch_id = 0
        self._is_user_seeking = False
        self.trending_tracks = []
        self.menu = None
        self.details_dialog = None
        self.queue_dialog = None
        self.history_dialog = None
        self.sleep_timer_dialog = None
        self.sleep_timer_event = None
        self.sleep_on_track_end = False

        # Initialize notification controller
        self.notif_mgr = PlaybackNotificationManager()

        # Register background broadcast receiver for notification & bluetooth actions
        if platform == 'android':
            try:
                from android.broadcast import BroadcastReceiver  # type: ignore
                from jnius import autoclass  # type: ignore

                Intent = autoclass('android.content.Intent')
                KeyEvent = autoclass('android.view.KeyEvent')

                def _on_notification_action(context, intent):
                    if not intent:
                        return
                    action = intent.getAction()

                    # 1. On-screen notification buttons
                    if action == PlaybackNotificationManager.ACTION_TOGGLE:
                        self._toggle_play()
                    elif action == PlaybackNotificationManager.ACTION_NEXT:
                        self._play_next()
                    elif action == PlaybackNotificationManager.ACTION_PREV:
                        self._play_prev()

                    # 2. Bluetooth and wired headset clicks
                    elif action == Intent.ACTION_MEDIA_BUTTON:
                        key_event = intent.getParcelableExtra(Intent.EXTRA_KEY_EVENT)
                        if key_event and key_event.getAction() == KeyEvent.ACTION_DOWN:
                            code = key_event.getKeyCode()
                            if code in (KeyEvent.KEYCODE_MEDIA_PLAY_PAUSE, KeyEvent.KEYCODE_HEADSETHOOK):
                                self._toggle_play()
                            elif code == KeyEvent.KEYCODE_MEDIA_PLAY:
                                if not self.audio.is_playing:
                                    self._toggle_play()
                            elif code == KeyEvent.KEYCODE_MEDIA_PAUSE:
                                if self.audio.is_playing:
                                    self._toggle_play()
                            elif code == KeyEvent.KEYCODE_MEDIA_NEXT:
                                self._play_next()
                            elif code == KeyEvent.KEYCODE_MEDIA_PREVIOUS:
                                self._play_prev()

                self._notif_receiver = BroadcastReceiver(
                    _on_notification_action,
                    actions=[
                        PlaybackNotificationManager.ACTION_PREV,
                        PlaybackNotificationManager.ACTION_TOGGLE,
                        PlaybackNotificationManager.ACTION_NEXT,
                        Intent.ACTION_MEDIA_BUTTON,
                    ]
                )
                self._notif_receiver.start()
            except Exception as r_err:
                print(f"[Receiver Init Error] {r_err}")

        # State restoration tracking
        self.restored_position = 0.0
        self.is_restored_state = False
        self._ticks_since_save = 0

        self.screen = PlayerScreen()
        self._bind_events()

        # 1. Restore previous session after UI mounts
        Clock.schedule_once(lambda dt: self._restore_last_playback_state(), 0.05)

        # 2. Schedule progress bar and periodic state save
        Clock.schedule_interval(self._update_progress, 0.25)

        # 3. Load randomized discovery tracks on launch
        threading.Thread(target=self._load_dynamic_home_music, daemon=True).start()

        return self.screen

    def on_pause(self):
        return True

    def on_resume(self):
        pass

    def on_stop(self):
        """Saves exact state when app closes."""
        self._persist_current_state()

        if hasattr(self, 'notif_mgr') and self.notif_mgr:
            self.notif_mgr.cancel()
        if hasattr(self, '_notif_receiver') and self._notif_receiver:
            self._notif_receiver.stop()

    def _persist_current_state(self):
        if self.current_track:
            pos, _ = self.audio.get_progress()
            target_pos = pos if pos > 0 else self.restored_position
            self.playlist_mgr.save_last_playback(self.current_track, target_pos)

    def _restore_last_playback_state(self):
        """Restores the last stopped song and timestamp into the mini-player."""
        last_track, last_pos = self.playlist_mgr.get_last_playback()
        if not last_track:
            return

        self.current_track = last_track
        self.restored_position = float(last_pos or 0.0)
        self.is_restored_state = True

        title = last_track.get('title', 'Unknown Track')
        artist = last_track.get('uploader', 'Unknown Artist')
        duration = float(last_track.get('duration') or 0.0)

        # Configure UI labels
        self.screen.mini_title.text = title
        self.screen.mini_artist.text = artist
        self.screen.full_title.text = title
        self.screen.full_artist.text = artist
        self.screen.full_header_sub.text = title[:24]

        # Configure timeline and sliders
        self.screen.time_current.text = format_time(self.restored_position)
        self.screen.time_total.text = format_time(duration) if duration > 0 else "--:--"

        if duration > 0:
            pct = max(0.0, min(100.0, (self.restored_position / duration) * 100.0))
            self.screen.mini_progress.value = pct
            self.screen.full_slider.value = pct

        # Configure AudioController state in paused mode
        self.audio.current_duration = duration
        self.audio.seek_offset = self.restored_position
        self.audio.is_paused = True
        self.audio.is_playing = False
        self.audio.queue = [last_track]
        self.audio.current_index = 0

        # Load cached artwork if available
        track_id = last_track.get('id', 'temp')
        cache_file = os.path.join(self._get_cache_dir(), f"{track_id}.jpg")
        if os.path.exists(cache_file):
            self._apply_thumbnail(cache_file)

        # Set like button state
        is_fav = self.playlist_mgr.is_favorite(track_id)
        self._update_like_button_ui(is_fav)

    def _bind_events(self):
        # Bottom Navigation
        self.screen.nav_home.on_release = self._show_home_tab
        self.screen.nav_search.on_release = self._show_search_tab
        self.screen.nav_library.on_release = self._show_library_tab

        # Top Bar Refresh & History Buttons
        self.screen.btn_refresh.on_release = self._on_refresh_home
        self.screen.btn_history.on_release = self._show_history_dialog

        # Search
        self.screen.search_input.bind(on_text_validate=self._perform_search)
        self.screen.btn_search_go.on_release = self._perform_search

        # Category Chips
        for chip in self.screen.chips_box.children:
            chip.bind(on_release=lambda btn: self._on_chip_selected(btn.text))

        # Open/Close Full Player
        self.screen.mini_artwork.bind(on_touch_down=self._on_mini_content_touch)
        self.screen.mini_text_box.bind(on_touch_down=self._on_mini_content_touch)
        self.screen.btn_close_full.on_release = self._close_full_player
        self.screen.top_drag_bar.bind(
            on_touch_down=lambda inst, touch: self._close_full_player() if inst.collide_point(*touch.pos) else False
        )

        # Mini Player Controls
        self.screen.btn_mini_play.on_release = self._toggle_play
        self.screen.btn_mini_next.on_release = self._play_next
        self.screen.btn_mini_more.on_release = lambda: self._open_song_menu(self.screen.btn_mini_more)

        # Full Screen Controls
        self.screen.btn_full_play_capsule.bind(on_release=lambda x: self._toggle_play())
        self.screen.capsule_icon.on_release = self._toggle_play
        self.screen.btn_full_prev.on_release = self._play_prev
        self.screen.btn_full_next.on_release = self._play_next
        self.screen.btn_full_shuffle.on_release = self._toggle_shuffle
        self.screen.btn_full_repeat.on_release = self._cycle_repeat
        self.screen.btn_like.on_release = self._toggle_like
        self.screen.btn_share.on_release = self._copy_current_link
        self.screen.btn_more.on_release = lambda: self._open_song_menu(self.screen.btn_more)

        # Utility Bar Buttons
        self.screen.btn_queue.on_release = self._show_queue_dialog
        self.screen.btn_timer.on_release = self._open_sleep_timer_dialog

        # Scrubbing
        for slider in (self.screen.mini_progress, self.screen.full_slider):
            slider.bind(on_touch_down=self._on_slider_touch_down)
            slider.bind(on_touch_up=self._on_slider_touch_up)
            slider.bind(value=self._on_slider_value_change)

    def _on_mini_content_touch(self, instance, touch):
        if instance.collide_point(*touch.pos):
            self._open_full_player()
            return True
        return False

    # ----------------- RECENTLY PLAYED (HISTORY) DIALOG -----------------
    def _show_history_dialog(self):
        recent_tracks = self.playlist_mgr.get_history()

        scroll = MDScrollView(size_hint=(1, None), height=dp(340))
        list_widget = MDList()
        scroll.add_widget(list_widget)

        if not recent_tracks:
            list_widget.add_widget(OneLineIconListItem(text="No recently played songs yet!"))
        else:
            for idx, track in enumerate(recent_tracks):
                item = TwoLineAvatarIconListItem(
                    text=track.get('title', 'Unknown')[:34],
                    secondary_text=track.get('uploader', 'Unknown')[:26]
                )
                item.add_widget(IconLeftWidget(icon="history", theme_text_color="Custom", text_color=(0.92, 0.82, 0.60, 1)))
                item.bind(on_release=lambda inst, t=track: self._play_from_history(t))
                list_widget.add_widget(item)

        if self.history_dialog:
            self.history_dialog.dismiss()

        self.history_dialog = MDDialog(
            title="Recently Played (Last 20)",
            type="custom",
            content_cls=scroll,
            buttons=[
                MDRaisedButton(
                    text="CLOSE",
                    md_bg_color=(0.25, 0.24, 0.17, 1),
                    on_release=lambda x: self.history_dialog.dismiss()
                )
            ],
        )
        self.history_dialog.open()

    def _play_from_history(self, track: dict):
        if self.history_dialog:
            self.history_dialog.dismiss()
        self._start_new_radio_mix(track)

    # ----------------- SLEEP TIMER SYSTEM -----------------
    def _open_sleep_timer_dialog(self):
        box = MDBoxLayout(orientation="vertical", adaptive_height=True, spacing=dp(4))

        options = [
            ("15 Minutes", 15),
            ("30 Minutes (Recommended)", 30),
            ("45 Minutes", 45),
            ("60 Minutes", 60),
            ("End of Current Track", "end_track"),
        ]

        if self.sleep_timer_event or self.sleep_on_track_end:
            options.append(("Turn Off Timer", "cancel"))

        for label, val in options:
            is_cancel = (val == "cancel")
            btn = MDRaisedButton(
                text=label,
                size_hint_x=1,
                elevation=0,
                md_bg_color=(0.35, 0.15, 0.15, 1) if is_cancel else (0.22, 0.21, 0.15, 1),
                text_color=(1, 0.6, 0.6, 1) if is_cancel else (0.95, 0.95, 0.95, 1),
                on_release=lambda inst, v=val: self._handle_timer_selection(v)
            )
            box.add_widget(btn)

        if self.sleep_timer_dialog:
            self.sleep_timer_dialog.dismiss()

        self.sleep_timer_dialog = MDDialog(
            title="Sleep Timer",
            type="custom",
            content_cls=box,
            buttons=[
                MDFlatButton(
                    text="DISMISS",
                    on_release=lambda x: self.sleep_timer_dialog.dismiss()
                )
            ],
        )
        self.sleep_timer_dialog.open()

    def _handle_timer_selection(self, val):
        if self.sleep_timer_dialog:
            self.sleep_timer_dialog.dismiss()

        if self.sleep_timer_event:
            self.sleep_timer_event.cancel()
            self.sleep_timer_event = None
        self.sleep_on_track_end = False

        if val == "cancel":
            self.screen.btn_timer.icon = "moon-waning-crescent"
            self.screen.btn_timer.text_color = (0.8, 0.8, 0.8, 1)
            self._set_artist_text("Sleep timer canceled")
            return

        if val == "end_track":
            self.sleep_on_track_end = True
            self.screen.btn_timer.icon = "bed-clock"
            self.screen.btn_timer.text_color = (0.92, 0.82, 0.60, 1)
            self._set_artist_text("Playback will stop after this song")
            return

        seconds = val * 60
        self.sleep_timer_event = Clock.schedule_once(self._on_sleep_timer_triggered, seconds)

        self.screen.btn_timer.icon = "bed-clock"
        self.screen.btn_timer.text_color = (0.92, 0.82, 0.60, 1)
        self._set_artist_text(f"Sleep timer set for {val} minutes")

    def _on_sleep_timer_triggered(self, dt):
        self.audio.stop()
        self._update_play_button_ui(is_playing=False)
        self.sleep_timer_event = None
        self.sleep_on_track_end = False
        self.screen.btn_timer.icon = "moon-waning-crescent"
        self.screen.btn_timer.text_color = (0.8, 0.8, 0.8, 1)
        self._set_artist_text("Sleep timer finished. Playback stopped.")

    # ----------------- SIMILAR SONGS & QUEUE DIALOG -----------------
    def _fetch_similar_and_build_loop_queue(self, seed_track: dict):
        def _worker():
            similar = self.search_engine.get_similar_tracks(seed_track, count=8)
            full_queue = [seed_track] + similar

            def _apply_queue(dt):
                self.audio.load_queue(full_queue, start_index=0)
                self.audio.set_repeat_mode("all")
                self.screen.btn_full_repeat.icon = "repeat"
                self.screen.btn_full_repeat.text_color = (0.92, 0.82, 0.60, 1)

                if self.queue_dialog:
                    self._populate_queue_list_widget(full_queue)

            Clock.schedule_once(_apply_queue)

        threading.Thread(target=_worker, daemon=True).start()

    def _show_queue_dialog(self):
        scroll = MDScrollView(size_hint=(1, None), height=dp(320))
        self.queue_list_widget = MDList()
        scroll.add_widget(self.queue_list_widget)

        self._populate_queue_list_widget(self.audio.queue)

        if self.queue_dialog:
            self.queue_dialog.dismiss()

        self.queue_dialog = MDDialog(
            title="Up Next (Similar Mix - Looping)",
            type="custom",
            content_cls=scroll,
            buttons=[
                MDRaisedButton(
                    text="CLOSE",
                    md_bg_color=(0.25, 0.24, 0.17, 1),
                    on_release=lambda x: self.queue_dialog.dismiss()
                )
            ],
        )
        self.queue_dialog.open()

    def _populate_queue_list_widget(self, queue: list[dict]):
        if not hasattr(self, 'queue_list_widget') or not self.queue_list_widget:
            return

        self.queue_list_widget.clear_widgets()
        if not queue:
            self.queue_list_widget.add_widget(OneLineIconListItem(text="Loading similar tracks..."))
            return

        for idx, track in enumerate(queue):
            is_active = (idx == self.audio.current_index)
            title = track.get('title', 'Unknown')[:34]
            artist = track.get('uploader', 'Unknown')[:26]

            item = TwoLineAvatarIconListItem(
                text=f"{'▶ ' if is_active else ''}{title}",
                secondary_text=artist
            )
            icon = "play-circle" if is_active else "music-note"
            icon_color = (0.92, 0.82, 0.60, 1) if is_active else (0.6, 0.6, 0.6, 1)
            item.add_widget(IconLeftWidget(icon=icon, theme_text_color="Custom", text_color=icon_color))
            item.bind(on_release=lambda inst, i=idx: self._select_queue_item(i))
            self.queue_list_widget.add_widget(item)

    def _select_queue_item(self, index: int):
        if self.queue_dialog:
            self.queue_dialog.dismiss()
        if 0 <= index < len(self.audio.queue):
            self.audio.current_index = index
            self.play_track(self.audio.queue[index])

    # ----------------- THREE-DOTS CONTEXT MENU -----------------
    def _open_song_menu(self, caller_widget):
        if not self.current_track:
            return

        menu_items = [
            {
                "viewclass": "OneLineListItem",
                "text": "View Crash Logs",
                "on_release": lambda: self._trigger_menu_action(self.open_crash_log_viewer),
            },
            {
                "viewclass": "OneLineListItem",
                "text": "Download Track",
                "height": dp(46),
                "on_release": lambda: self._handle_menu_action("download"),
            },
            {
                "viewclass": "OneLineListItem",
                "text": "Song Details",
                "height": dp(46),
                "on_release": lambda: self._handle_menu_action("details"),
            },
            {
                "viewclass": "OneLineListItem",
                "text": "Add to Playlist",
                "height": dp(46),
                "on_release": lambda: self._handle_menu_action("playlist"),
            },
            {
                "viewclass": "OneLineListItem",
                "text": "Copy Song Link",
                "height": dp(46),
                "on_release": lambda: self._handle_menu_action("copy"),
            }
        ]

        if self.menu:
            self.menu.dismiss()

        self.menu = MDDropdownMenu(
            caller=caller_widget,
            items=menu_items,
            width_mult=4,
            ver_growth="up",
            hor_growth="left",
            elevation=4
        )
        self.menu.open()

    def _handle_menu_action(self, action: str):
        if self.menu:
            self.menu.dismiss()

        if action == "download":
            self._download_active_track()
        elif action == "details":
            self._show_song_details()
        elif action == "playlist":
            self._open_add_to_playlist_dialog()
        elif action == "copy":
            self._copy_current_link()

    def _download_active_track(self):
        if not self.current_track:
            return

        if self.current_track.get('local_path') and os.path.exists(self.current_track['local_path']):
            self._set_artist_text("Already available offline")
            return

        title = self.current_track.get('title', 'Track')[:24]
        self._set_artist_text(f"Downloading: {title}...")

        def _worker():
            url = self.current_track.get('webpage_url') or f"https://www.youtube.com/watch?v={self.current_track.get('id')}"
            success = self.downloader.download_track(url, self.current_track.get('title', 'track'))
            Clock.schedule_once(lambda dt: self._set_artist_text(
                "Saved to downloads/" if success else "Download failed"
            ))

        threading.Thread(target=_worker, daemon=True).start()

    def _trigger_download(self, track_data: dict):
        """Dispatches downloads to a daemon thread to prevent UI lockups."""
        self._set_artist_text("Downloading song...")

        def _worker():
            url = track_data.get('webpage_url') or f"https://www.youtube.com/watch?v={track_data.get('id')}"
            success = self.downloader.download_track(url, track_data.get('title', 'track'))
            Clock.schedule_once(lambda dt: self._set_artist_text(
                "Download finished!" if success else "Download failed"
            ))

        threading.Thread(target=_worker, daemon=True).start()

    def _set_artist_text(self, text: str):
        self.screen.mini_artist.text = text
        self.screen.full_artist.text = text

    def _copy_current_link(self):
        if not self.current_track:
            return
        url = self.current_track.get('webpage_url') or f"https://www.youtube.com/watch?v={self.current_track.get('id', '')}"
        Clipboard.copy(url)
        self._set_artist_text("Link copied to clipboard!")

    # ----------------- SONG DETAILS MODAL -----------------
    def _show_song_details(self):
        if not self.current_track:
            return

        track = self.current_track
        dur = float(self.audio.current_duration or track.get('duration') or 0.0)

        is_offline = bool(track.get('local_path') and os.path.exists(track['local_path']))
        status_text = "Offline Storage (Local)" if is_offline else "Online Stream (Vorbis OGG / 192kbps)"
        source_path = track.get('local_path') if is_offline else track.get('webpage_url', 'YouTube Music')

        container = MDBoxLayout(
            orientation="vertical",
            spacing=dp(8),
            padding=[dp(8), dp(4), dp(8), dp(4)],
            adaptive_height=True
        )

        detail_fields = [
            ("Track Title", track.get('title', 'Unknown Track')),
            ("Artist / Channel", track.get('uploader', 'Unknown Artist')),
            ("Duration", format_time(dur)),
            ("Audio Quality", status_text),
            ("Track ID", track.get('id', 'N/A')),
            ("File Source", source_path)
        ]

        for label, val in detail_fields:
            row = MDBoxLayout(orientation="vertical", spacing=dp(1), adaptive_height=True)
            row.add_widget(MDLabel(text=label.upper(), font_style="Caption", theme_text_color="Secondary", size_hint_y=None, height=dp(14)))
            row.add_widget(MDLabel(text=str(val), font_style="Body2", bold=True, shorten=True, shorten_from="center", size_hint_y=None, height=dp(20)))
            container.add_widget(row)

        if self.details_dialog:
            self.details_dialog.dismiss()

        self.details_dialog = MDDialog(
            title="Song Details",
            type="custom",
            content_cls=container,
            buttons=[
                MDRaisedButton(
                    text="DONE",
                    md_bg_color=(0.25, 0.24, 0.17, 1),
                    on_release=lambda x: self.details_dialog.dismiss()
                )
            ],
        )
        self.details_dialog.open()

    # ----------------- SLIDE-UP MODAL CONTROLS -----------------
    def _open_full_player(self, *args):
        Animation(pos_hint={'y': 0}, duration=0.28, t='out_quad').start(self.screen.full_player)

    def _close_full_player(self, *args):
        Animation(pos_hint={'y': -1}, duration=0.22, t='in_quad').start(self.screen.full_player)

    # ----------------- FAVORITES SYSTEM -----------------
    def _toggle_like(self):
        if not self.current_track:
            return

        is_fav = self.playlist_mgr.toggle_favorite(self.current_track)
        anim = Animation(opacity=0.3, duration=0.08) + Animation(opacity=1.0, duration=0.1)
        anim.start(self.screen.btn_like)

        self._update_like_button_ui(is_fav)

        if self.active_tab == "library":
            self._render_library()

    def _update_like_button_ui(self, is_liked: bool):
        if is_liked:
            self.screen.btn_like.icon = "heart"
            self.screen.btn_like.text_color = (0.92, 0.22, 0.22, 1)
        else:
            self.screen.btn_like.icon = "heart-outline"
            self.screen.btn_like.text_color = (1, 1, 1, 1)

    # ----------------- REFRESH & DISCOVERY -----------------
    def _on_refresh_home(self):
        anim = Animation(opacity=0.3, duration=0.1) + Animation(opacity=1.0, duration=0.15)
        anim.start(self.screen.btn_refresh)

        self.screen.section_label.text = "Discovering new picks..."
        self.screen.grid.clear_widgets()

        threading.Thread(target=self._load_dynamic_home_music, daemon=True).start()

    # ----------------- DYNAMIC HOME & SPEED DIAL -----------------
    def _load_dynamic_home_music(self, query=None):
        if query:
            tracks = self.search_engine.search_tracks(query, max_results=24)
        else:
            tracks = self.search_engine.get_trending_tracks(count=24)

        self.trending_tracks = tracks
        Clock.schedule_once(lambda dt: self._populate_speed_dial(tracks))

    def _populate_speed_dial(self, tracks: list[dict]):
        if self.screen.section_label.text == "Discovering new picks...":
            self.screen.section_label.text = "Speed dial"

        self.screen.grid.clear_widgets()
        for idx, track in enumerate(tracks):
            card = SongCard(
                track_data=track,
                on_click_callback=lambda t: self._start_new_radio_mix(t)
            )
            self.screen.grid.add_widget(card)

    def _start_new_radio_mix(self, track: dict):
        self.is_restored_state = False
        self.restored_position = 0.0
        self.audio.load_queue([track], start_index=0)
        self.play_track(track)
        self._fetch_similar_and_build_loop_queue(track)

    def _on_chip_selected(self, category: str):
        self.screen.section_label.text = f"{category} picks"
        self.screen.grid.clear_widgets()
        threading.Thread(
            target=lambda: self._load_dynamic_home_music(f"Best {category} music playlist hits"),
            daemon=True
        ).start()

    # ----------------- NAVIGATION ROUTING -----------------
    def _show_home_tab(self):
        self.active_tab = "home"
        self._update_nav_colors(self.screen.nav_home)
        self.screen.header_title.text = "Home"

        if self.screen.search_box in self.screen.root_layout.children:
            self.screen.root_layout.remove_widget(self.screen.search_box)
        self.screen.chips_scroll.height = dp(36)
        self.screen.chips_scroll.opacity = 1
        self.screen.section_label.opacity = 1
        self.screen.section_label.height = dp(30)
        self.screen.section_label.text = "Speed dial"
        self.screen.list_view.clear_widgets()
        self._populate_speed_dial(self.trending_tracks)

    def _show_search_tab(self):
        self.active_tab = "search"
        self._update_nav_colors(self.screen.nav_search)
        self.screen.header_title.text = "Search"

        if self.screen.search_box not in self.screen.root_layout.children:
            self.screen.root_layout.add_widget(self.screen.search_box, index=3)
        self.screen.chips_scroll.height = 0
        self.screen.chips_scroll.opacity = 0
        self.screen.section_label.opacity = 0
        self.screen.section_label.height = 0
        self.screen.grid.clear_widgets()
        self.screen.list_view.clear_widgets()

    def _show_library_tab(self):
        self.active_tab = "library"
        self._update_nav_colors(self.screen.nav_library)
        self.screen.header_title.text = "Library"

        if self.screen.search_box in self.screen.root_layout.children:
            self.screen.root_layout.remove_widget(self.screen.search_box)
        self.screen.chips_scroll.height = 0
        self.screen.chips_scroll.opacity = 0
        self.screen.section_label.opacity = 1
        self.screen.section_label.height = dp(30)
        self.screen.section_label.text = "Your Music & Collections"
        self.screen.grid.clear_widgets()
        self._render_library()

    def _update_nav_colors(self, active_btn):
        for btn in (self.screen.nav_home, self.screen.nav_search, self.screen.nav_library):
            btn.text_color = (1, 1, 1, 1) if btn == active_btn else (0.5, 0.5, 0.5, 1)

    # ----------------- SEARCH & RESULTS -----------------
    def _perform_search(self, *args):
        query = self.screen.search_input.text.strip()
        if not query:
            return

        self.screen.list_view.clear_widgets()
        def _worker():
            results = self.search_engine.search_tracks(query, max_results=10)
            Clock.schedule_once(lambda dt: self._populate_search_results(results))
        threading.Thread(target=_worker, daemon=True).start()

    def _populate_search_results(self, results: list[dict]):
        self.screen.list_view.clear_widgets()
        for idx, track in enumerate(results):
            item = TwoLineAvatarIconListItem(
                text=track.get('title', 'Unknown')[:36],
                secondary_text=track.get('uploader', 'Unknown')[:28]
            )
            item.add_widget(IconLeftWidget(icon="music-circle-outline"))
            btn_dl = IconRightWidget(icon="download")
            btn_dl.bind(on_release=lambda inst, t=track, b=btn_dl: self._start_download_from_list(t, b))
            item.add_widget(btn_dl)
            item.bind(on_release=lambda inst, t=track: self._start_new_radio_mix(t))
            self.screen.list_view.add_widget(item)

    def _start_download_from_list(self, track: dict, button: IconRightWidget):
        button.disabled = True
        button.icon = "progress-download"
        self._trigger_download(track)
        Clock.schedule_once(lambda dt: setattr(button, 'icon', 'check-circle'), 3.0)

    # ----------------- PLAYBACK CONTROLLER -----------------
    def play_track(self, track: dict, start_pos: float = 0.0):
        self.audio.stop()
        self._update_play_button_ui(is_playing=False)
        self.screen.mini_progress.value = 0
        self.screen.full_slider.value = 0

        self.current_track = track
        title = track.get('title', 'Unknown')
        artist = track.get('uploader', 'Unknown Artist')

        self.playlist_mgr.add_to_history(track)

        is_fav = self.playlist_mgr.is_favorite(track.get('id', ''))
        self._update_like_button_ui(is_fav)

        self.screen.mini_title.text = title
        self.screen.mini_artist.text = "Loading audio..."
        self.screen.full_title.text = title
        self.screen.full_artist.text = artist
        self.screen.full_header_sub.text = title[:24]

        self._current_fetch_id += 1
        fetch_id = self._current_fetch_id

        # 1. Local Playback
        if track.get('local_path') and os.path.exists(track['local_path']):
            self.screen.mini_artwork.source = "assets/placeholder.png"
            self.screen.full_artwork.source = "assets/placeholder.png"
            self.screen.mini_artist.text = track.get('uploader', 'Offline')
            dur = float(track.get('duration') or 0.0)
            if dur <= 0:
                try:
                    mf = mutagen.File(track['local_path'])
                    dur = float(mf.info.length) if mf and mf.info else 0.0
                except Exception:
                    dur = 0.0
            self.screen.time_total.text = format_time(dur)
            self.audio.play_local_file(track['local_path'], duration=dur, start_pos=start_pos)
            self._update_play_button_ui(is_playing=True)
            return

        # 2. Artwork Fetch
        track_id = track.get('id', 'temp')
        thumb_url = track.get('thumbnail')
        if thumb_url:
            def _download_artwork():
                if fetch_id != self._current_fetch_id:
                    return
                try:
                    cache_file = os.path.join(self._get_cache_dir(), f"{track_id}.jpg")
                    if not os.path.exists(cache_file):
                        import requests
                        headers = {'User-Agent': 'Mozilla/5.0'}
                        res = requests.get(thumb_url, headers=headers, timeout=10)
                        if res.status_code == 200:
                            with open(cache_file, "wb") as f:
                                f.write(res.content)

                    if fetch_id == self._current_fetch_id and os.path.exists(cache_file):
                        Clock.schedule_once(lambda dt: self._apply_thumbnail(cache_file), 0)
                except Exception as e:
                    print(f"[Thumbnail Download Error] {e}")

            threading.Thread(
                target=_download_artwork,
                name="ArtworkDownloadThread",
                daemon=True
            ).start()

        # 3. Background Audio Fetch
        def _fetch_audio():
            audio_path, duration = self.search_engine.prepare_audio_file(
                track.get('webpage_url', ''), track_id
            )
            if fetch_id != self._current_fetch_id:
                return
            if audio_path:
                self.audio.play_local_file(audio_path, duration=duration, start_pos=start_pos)

                def _update_ui(dt):
                    self.screen.mini_artist.text = track.get('uploader') or 'Unknown Artist'
                    self.screen.time_total.text = format_time(duration)
                    self._update_play_button_ui(is_playing=True)
                Clock.schedule_once(_update_ui, 0)
            else:
                Clock.schedule_once(lambda dt: setattr(self.screen.mini_artist, 'text', 'Playback failed'), 0)

        threading.Thread(target=_fetch_audio, name="AudioStreamThread", daemon=True).start()

    def _start_audio_playback(self, audio_path: str, duration: float, uploader: str, start_pos: float = 0.0):
        self.screen.mini_artist.text = uploader or 'Unknown Artist'
        self.screen.time_total.text = format_time(duration)
        self.audio.play_local_file(audio_path, duration=duration, start_pos=start_pos)
        self._update_play_button_ui(is_playing=True)

        if hasattr(self, 'notif_mgr') and self.notif_mgr:
            track = self.current_track or {}
            self.notif_mgr.show(
                title=track.get('title', 'Playing'),
                artist=uploader or 'Unknown Artist',
                is_playing=True
            )

    def _apply_thumbnail(self, path: str):
        if not path or not os.path.exists(path):
            return

        self.screen.mini_artwork.source = path
        self.screen.full_artwork.source = path

        try:
            self.screen.mini_artwork.reload()
            self.screen.full_artwork.reload()
        except Exception:
            pass

    def _toggle_play(self):
        if self.is_restored_state and self.current_track and not self.audio.is_playing:
            self.is_restored_state = False
            self.play_track(self.current_track, start_pos=self.restored_position)
            return

        self.audio.toggle_play_pause()
        self._update_play_button_ui(self.audio.is_playing)
        self._persist_current_state()

    def _update_play_button_ui(self, is_playing: bool):
        self.screen.btn_mini_play.icon = "pause-circle" if is_playing else "play-circle"
        self.screen.capsule_icon.icon = "pause" if is_playing else "play"
        self.screen.capsule_label.text = "Pause" if is_playing else "Play"

        if hasattr(self, 'notif_mgr') and self.current_track:
            self.notif_mgr.show(
                title=self.current_track.get('title', 'Playing'),
                artist=self.current_track.get('uploader', 'Unknown Artist'),
                is_playing=is_playing
            )

    def _play_next(self, *args):
        if self.sleep_on_track_end:
            self._on_sleep_timer_triggered(None)
            return

        self.is_restored_state = False
        track = self.audio.next_track()
        if track:
            self.play_track(track)
        else:
            self.audio.stop()
            self._update_play_button_ui(is_playing=False)
            self.screen.mini_progress.value = 0
            self.screen.full_slider.value = 0

    def _play_prev(self):
        self.is_restored_state = False
        track = self.audio.prev_track()
        if track:
            self.play_track(track)

    def _toggle_shuffle(self):
        self.audio.toggle_shuffle()
        anim = Animation(opacity=0.3, duration=0.08) + Animation(opacity=1.0, duration=0.1)
        anim.start(self.screen.btn_full_shuffle)
        if self.audio.is_shuffled:
            self.screen.btn_full_shuffle.icon = "shuffle"
            self.screen.btn_full_shuffle.text_color = (0.92, 0.82, 0.60, 1)
        else:
            self.screen.btn_full_shuffle.icon = "shuffle-disabled"
            self.screen.btn_full_shuffle.text_color = (0.5, 0.5, 0.5, 1)

    def _cycle_repeat(self):
        modes = ["off", "all", "one"]
        new_mode = modes[(modes.index(self.audio.repeat_mode) + 1) % 3]
        self.audio.set_repeat_mode(new_mode)
        icons = {"off": "repeat-off", "all": "repeat", "one": "repeat-once"}
        self.screen.btn_full_repeat.icon = icons[new_mode]
        self.screen.btn_full_repeat.text_color = (0.92, 0.82, 0.60, 1) if new_mode != "off" else (0.5, 0.5, 0.5, 1)

    # ----------------- SLIDER & TIME SYNC -----------------
    def _on_slider_touch_down(self, instance, touch):
        if instance.collide_point(*touch.pos):
            self._is_user_seeking = True
        return False

    def _on_slider_value_change(self, instance, value):
        if self._is_user_seeking and self.audio.current_duration > 0:
            target_sec = (value / 100.0) * self.audio.current_duration
            self.screen.time_current.text = format_time(target_sec)

    def _on_slider_touch_up(self, instance, touch):
        if self._is_user_seeking:
            self._is_user_seeking = False
            ratio = max(0.0, min(1.0, instance.value / 100.0))
            if self.is_restored_state and self.current_track:
                self.is_restored_state = False
                self.restored_position = ratio * self.audio.current_duration
                self.play_track(self.current_track, start_pos=self.restored_position)
            else:
                self.audio.seek(ratio)
                self._update_play_button_ui(is_playing=True)
            self._persist_current_state()
        return False

    def _update_progress(self, dt):
        if not self.audio.is_playing and not self.audio.is_paused:
            return

        pos, length = self.audio.get_progress()

        if not self._is_user_seeking and length > 0 and self.audio.is_playing:
            pct = max(0.0, min(100.0, (pos / length) * 100.0))
            self.screen.mini_progress.value = pct
            self.screen.full_slider.value = pct
            self.screen.time_current.text = format_time(pos)
            self.screen.time_total.text = format_time(length)

        self._ticks_since_save += 1
        if self._ticks_since_save >= 12 and self.audio.is_playing:
            self._ticks_since_save = 0
            self._persist_current_state()

        if self.audio.is_finished():
            self._play_next()

    # ----------------- PLAYLISTS & COLLECTIONS -----------------
    def _open_add_to_playlist_dialog(self):
        if not self.current_track:
            return

        playlists = self.playlist_mgr.get_all_playlists()
        box = MDBoxLayout(orientation="vertical", adaptive_height=True, spacing=dp(8))

        dialog = MDDialog(
            title="Add to Playlist",
            type="custom",
            content_cls=box,
            buttons=[MDFlatButton(text="CANCEL", on_release=lambda x: dialog.dismiss())]
        )

        for name in playlists:
            btn = MDRaisedButton(
                text=name,
                size_hint_x=1,
                on_release=lambda inst, n=name: self._confirm_add_playlist(n, dialog)
            )
            box.add_widget(btn)

        dialog.open()

    def _confirm_add_playlist(self, name: str, dialog):
        dialog.dismiss()
        self.playlist_mgr.add_to_playlist(name, self.current_track)
        self._set_artist_text(f"Added to {name}!")

    # ----------------- LIBRARY VIEW -----------------
    def _render_library(self):
        self.screen.list_view.clear_widgets()

        favorites = self.playlist_mgr.get_favorites()
        fav_header = TwoLineAvatarIconListItem(
            text="Liked Songs",
            secondary_text=f"{len(favorites)} favorite tracks"
        )
        fav_header.add_widget(IconLeftWidget(icon="heart", theme_text_color="Custom", text_color=(0.92, 0.22, 0.22, 1)))
        fav_header.bind(on_release=lambda x: self._render_liked_songs_list())
        self.screen.list_view.add_widget(fav_header)

        offline_tracks = self.playlist_mgr.get_offline_tracks()
        dl_header = TwoLineAvatarIconListItem(
            text="Downloaded Songs",
            secondary_text=f"{len(offline_tracks)} tracks offline"
        )
        dl_header.add_widget(IconLeftWidget(icon="cellphone-arrow-down"))
        dl_header.bind(on_release=lambda x: self._render_offline_songs_list())
        self.screen.list_view.add_widget(dl_header)

    def _render_liked_songs_list(self):
        self.screen.list_view.clear_widgets()
        favorites = self.playlist_mgr.get_favorites()

        back_item = OneLineIconListItem(text="<- Back to Library (Liked Songs)")
        back_item.add_widget(IconLeftWidget(icon="arrow-left"))
        back_item.bind(on_release=lambda x: self._render_library())
        self.screen.list_view.add_widget(back_item)

        if not favorites:
            self.screen.list_view.add_widget(OneLineIconListItem(text="No liked tracks yet. Tap heart while playing!"))
            return

        for idx, track in enumerate(favorites):
            item = TwoLineAvatarIconListItem(
                text=track.get('title', 'Unknown')[:36],
                secondary_text=track.get('uploader', 'Unknown')[:28]
            )
            item.add_widget(IconLeftWidget(icon="heart", theme_text_color="Custom", text_color=(0.92, 0.22, 0.22, 1)))
            item.bind(on_release=lambda inst, t=track: self._start_new_radio_mix(t))
            self.screen.list_view.add_widget(item)

    def _render_offline_songs_list(self):
        self.screen.list_view.clear_widgets()
        offline_tracks = self.playlist_mgr.get_offline_tracks()

        back_item = OneLineIconListItem(text="<- Back to Library (Downloads)")
        back_item.add_widget(IconLeftWidget(icon="arrow-left"))
        back_item.bind(on_release=lambda x: self._render_library())
        self.screen.list_view.add_widget(back_item)

        for idx, track in enumerate(offline_tracks):
            item = TwoLineAvatarIconListItem(
                text=track.get('title', 'Unknown')[:36],
                secondary_text="Offline Storage"
            )
            item.add_widget(IconLeftWidget(icon="cellphone-arrow-down"))
            item.bind(on_release=lambda inst, t=track: self._start_new_radio_mix(t))
            self.screen.list_view.add_widget(item)


# ----------------- CRASH REPORTER & ENTRY POINT -----------------
class CrashReporterApp(App):
    """Displays error traceback directly on mobile screen if initialization fails."""
    def __init__(self, error_msg, **kwargs):
        super().__init__(**kwargs)
        self.error_msg = error_msg

    def build(self):
        Window.clearcolor = (0.1, 0.1, 0.1, 1)
        sv = ScrollView(size_hint=(1, 1))
        lbl = Label(
            text=f"[CRASH TRACEBACK]\n\n{self.error_msg}",
            color=(1, 0.3, 0.3, 1),
            font_size="11sp",
            size_hint_y=None,
            padding=(20, 20),
            halign="left",
            valign="top"
        )
        lbl.bind(texture_size=lambda instance, val: setattr(instance, 'height', val[1]))
        lbl.bind(width=lambda instance, val: setattr(instance, 'text_size', (val - 40, None)))
        sv.add_widget(lbl)
        return sv


if __name__ == '__main__':
    try:
        MusicPlayerApp().run()
    except Exception:
        CrashReporterApp(traceback.format_exc()).run()