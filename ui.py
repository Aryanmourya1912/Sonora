import os
from kivy.metrics import dp
from kivy.animation import Animation
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.textinput import TextInput
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.gridlayout import MDGridLayout
from kivymd.uix.scrollview import MDScrollView
from kivymd.uix.card import MDCard
from kivymd.uix.label import MDLabel, MDIcon
from kivymd.uix.button import MDIconButton, MDRaisedButton
from kivymd.uix.slider import MDSlider
from kivymd.uix.list import MDList
from kivymd.uix.fitimage import FitImage


class ClickableCard(MDCard):
    """Touch-safe card that dispatches on_release without Python MRO conflicts."""
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.register_event_type('on_release')

    def on_touch_down(self, touch):
        if self.disabled or not self.collide_point(*touch.pos):
            return super().on_touch_down(touch)
        if super().on_touch_down(touch):
            return True
        touch.grab(self)
        return True

    def on_touch_up(self, touch):
        if touch.grab_current is self:
            touch.ungrab(self)
            if not self.disabled and self.collide_point(*touch.pos):
                self.dispatch('on_release')
            return True
        return super().on_touch_up(touch)

    def on_release(self, *args):
        pass


class SongCard(ClickableCard):
    """Compact song card for the horizontal Speed Dial."""
    def __init__(self, track_data: dict, on_click_callback, **kwargs):
        super().__init__(**kwargs)
        self.track_data = track_data
        self.orientation = "vertical"
        self.size_hint = (None, None)
        self.size = (dp(110), dp(105))
        self.radius = [dp(12)]
        self.elevation = 1
        self.md_bg_color = (0.13, 0.16, 0.22, 1)
        self.padding = dp(5)
        self.spacing = dp(4)

        thumb = track_data.get('thumbnail') or "assets/placeholder.png"
        self.img = FitImage(
            source=thumb,
            size_hint=(1, 0.68),
            radius=[dp(10)]
        )
        self.add_widget(self.img)

        title = MDLabel(
            text=track_data.get('title', 'Unknown')[:16],
            font_style="Caption",
            theme_text_color="Primary",
            shorten=True,
            shorten_from="right",
            halign="center",
            size_hint_y=0.32
        )
        self.add_widget(title)
        self.bind(on_release=lambda x: on_click_callback(self.track_data))


class TwoStageBottomSheet(FloatLayout):
    """Two-stage bottom sheet supporting half-screen and full-screen expansion."""
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.size_hint = (1, 1)
        self.pos_hint = {'x': 0, 'y': -1}
        self.state = "closed"
        self.disabled = True
        self.opacity = 0

        # Dimmed backdrop
        self.backdrop = ClickableCard(
            size_hint=(1, 1),
            pos_hint={'x': 0, 'y': 0},
            md_bg_color=(0, 0, 0, 0.6),
            elevation=0
        )
        self.backdrop.bind(on_release=lambda x: self.close())
        self.add_widget(self.backdrop)

        # Bottom sheet container
        self.sheet = MDCard(
            orientation="vertical",
            size_hint=(1, 0.56),
            pos_hint={'x': 0, 'y': 0},
            radius=[dp(24), dp(24), 0, 0],
            md_bg_color=(0.08, 0.10, 0.14, 1),
            elevation=10,
            padding=[dp(16), dp(10), dp(16), dp(12)],
            spacing=dp(10)
        )

        # 1. Top Drag Handle
        self.handle_box = MDBoxLayout(size_hint=(1, None), height=dp(20))
        self.drag_pill = ClickableCard(
            size_hint=(None, None),
            size=(dp(44), dp(5)),
            pos_hint={'center_x': 0.5, 'center_y': 0.5},
            radius=[dp(3)],
            md_bg_color=(0.4, 0.45, 0.55, 1)
        )
        self.drag_pill.bind(on_release=lambda x: self.toggle_expand())
        self.handle_box.add_widget(self.drag_pill)
        self.sheet.add_widget(self.handle_box)

        # 2. Audio status bar preview pill
        self.preview_bar = MDCard(
            size_hint=(1, None),
            height=dp(38),
            radius=[dp(10)],
            md_bg_color=(0.74, 0.78, 0.96, 0.85),
            padding=[dp(12), dp(6)]
        )
        self.preview_icon = MDIcon(
            icon="volume-high",
            font_size="20sp",
            theme_text_color="Custom",
            text_color=(0.1, 0.12, 0.18, 1),
            pos_hint={'center_y': 0.5}
        )
        self.preview_bar.add_widget(self.preview_icon)
        self.sheet.add_widget(self.preview_bar)

        # 3. Quick Action Row
        self.quick_row = MDBoxLayout(size_hint_y=None, height=dp(72), spacing=dp(10))
        self.btn_radio = self._create_quick_card("radio-tower", "Start radio")
        self.btn_add_playlist = self._create_quick_card("playlist-plus", "Add to playlist")
        self.btn_copy = self._create_quick_card("link-variant", "Copy link")
        self.quick_row.add_widget(self.btn_radio)
        self.quick_row.add_widget(self.btn_add_playlist)
        self.quick_row.add_widget(self.btn_copy)
        self.sheet.add_widget(self.quick_row)

        # 4. Scrollable Action List
        self.scroll = MDScrollView(size_hint=(1, 1), bar_width=0)
        self.actions_list = MDBoxLayout(orientation="vertical", adaptive_height=True, spacing=dp(6))

        self.item_artist = self._create_list_item("account-music-outline", "View artist", "Artist details")
        self.item_album = self._create_list_item("album", "View album", "Album tracks")
        self.item_library = self._create_list_item("plus-box-outline", "Add to library", "Save to your favorites")
        self.item_speed_dial = self._create_list_item("pin-outline", "Pin to speed dial", "Add to Home screen")
        self.item_download = self._create_list_item("download-outline", "Download", "Save offline playback")
        self.item_details = self._create_list_item("information-outline", "Details", "View track audio specs")
        self.item_logs = self._create_list_item("bug-outline", "View Crash Logs", "Inspect diagnostic records")

        for item in (
            self.item_artist, self.item_album, self.item_library,
            self.item_speed_dial, self.item_download, self.item_details, self.item_logs
        ):
            self.actions_list.add_widget(item)

        self.scroll.add_widget(self.actions_list)
        self.sheet.add_widget(self.scroll)
        self.add_widget(self.sheet)

    def on_touch_down(self, touch):
        if self.state == "closed" or self.disabled:
            return False
        return super().on_touch_down(touch)

    def on_touch_move(self, touch):
        if self.state == "closed" or self.disabled:
            return False
        return super().on_touch_move(touch)

    def on_touch_up(self, touch):
        if self.state == "closed" or self.disabled:
            return False
        return super().on_touch_up(touch)

    def _create_quick_card(self, icon: str, label: str):
        card = ClickableCard(
            orientation="vertical",
            size_hint=(0.33, 1),
            radius=[dp(16)],
            md_bg_color=(0.14, 0.17, 0.23, 1),
            padding=[dp(6), dp(8)],
            spacing=dp(2)
        )
        ic = MDIcon(
            icon=icon,
            font_size="22sp",
            halign="center",
            pos_hint={'center_x': 0.5},
            theme_text_color="Custom",
            text_color=(0.9, 0.92, 0.98, 1)
        )
        lb = MDLabel(
            text=label,
            font_style="Caption",
            halign="center",
            theme_text_color="Custom",
            text_color=(0.75, 0.8, 0.9, 1),
            shorten=True
        )
        card.add_widget(ic)
        card.add_widget(lb)
        return card

    def _create_list_item(self, icon: str, title: str, subtitle: str = ""):
        card = ClickableCard(
            size_hint_y=None,
            height=dp(52),
            radius=[dp(14)],
            md_bg_color=(0.11, 0.13, 0.18, 1),
            padding=[dp(14), 0, dp(14), 0]
        )
        box = MDBoxLayout(orientation="horizontal", spacing=dp(14), pos_hint={'center_y': 0.5})
        ic = MDIcon(
            icon=icon,
            font_size="22sp",
            theme_text_color="Custom",
            text_color=(0.85, 0.88, 0.96, 1),
            pos_hint={'center_y': 0.5}
        )
        t_box = MDBoxLayout(orientation="vertical", pos_hint={'center_y': 0.5})
        t_lbl = MDLabel(text=title, font_style="Subtitle2", bold=True, theme_text_color="Primary")
        t_box.add_widget(t_lbl)
        if subtitle:
            s_lbl = MDLabel(text=subtitle, font_style="Caption", theme_text_color="Secondary", shorten=True)
            t_box.add_widget(s_lbl)

        box.add_widget(ic)
        box.add_widget(t_box)
        card.add_widget(box)
        return card

    def open_half(self):
        self.state = "half"
        self.disabled = False
        self.opacity = 1
        self.pos_hint = {'x': 0, 'y': 0}
        Animation(size_hint_y=0.56, duration=0.25, t='out_quad').start(self.sheet)

    def expand_full(self):
        self.state = "full"
        self.disabled = False
        self.opacity = 1
        Animation(size_hint_y=0.92, duration=0.25, t='out_quad').start(self.sheet)

    def toggle_expand(self):
        if self.state == "half":
            self.expand_full()
        else:
            self.open_half()

    def close(self):
        self.state = "closed"
        self.disabled = True
        anim = Animation(pos_hint={'x': 0, 'y': -1}, opacity=0, duration=0.22, t='in_quad')
        anim.start(self)


class PlayerScreen(FloatLayout):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        # ----------------- MAIN APP CONTAINER -----------------
        self.root_layout = MDBoxLayout(
            orientation="vertical",
            size_hint=(1, 1),
            md_bg_color=(0.04, 0.05, 0.07, 1)
        )

        # TOP BAR
        self.top_bar = MDBoxLayout(
            orientation="horizontal",
            size_hint_y=None,
            height=dp(54),
            padding=[dp(16), dp(8), dp(16), 0]
        )
        self.header_title = MDLabel(
            text="Home",
            font_style="H5",
            bold=True,
            theme_text_color="Primary"
        )
        self.btn_refresh = MDIconButton(icon="refresh", theme_text_color="Primary")
        self.btn_history = MDIconButton(icon="history", theme_text_color="Primary")
        self.top_bar.add_widget(self.header_title)
        self.top_bar.add_widget(self.btn_refresh)
        self.top_bar.add_widget(self.btn_history)
        self.root_layout.add_widget(self.top_bar)

        # MODERN SEARCH HEADER
        self.search_header = MDBoxLayout(
            orientation="horizontal",
            size_hint_y=None,
            height=dp(52),
            padding=[dp(8), 0, dp(12), 0],
            spacing=dp(8)
        )
        self.btn_search_back = MDIconButton(icon="arrow-left", theme_text_color="Primary")
        self.search_input = TextInput(
            hint_text="Search songs, artists...",
            background_color=(0, 0, 0, 0),
            foreground_color=(1, 1, 1, 1),
            hint_text_color=(0.55, 0.55, 0.65, 1),
            font_size="16sp",
            multiline=False,
            size_hint_y=None,
            height=dp(40),
            pos_hint={'center_y': 0.5}
        )
        self.btn_search_clear = MDIconButton(icon="close", theme_text_color="Secondary")
        self.search_header.add_widget(self.btn_search_back)
        self.search_header.add_widget(self.search_input)
        self.search_header.add_widget(self.btn_search_clear)

        # CATEGORY CHIPS SCROLL
        self.chips_scroll = MDScrollView(
            do_scroll_x=True,
            do_scroll_y=False,
            size_hint_y=None,
            height=dp(42),
            bar_width=0
        )
        self.chips_box = MDBoxLayout(
            orientation="horizontal",
            adaptive_width=True,
            spacing=dp(8),
            padding=[dp(16), 0, dp(16), 0]
        )
        for cat in ["Trending", "Podcasts", "Workout", "Feel good", "Focus", "Party", "Romance"]:
            btn = MDRaisedButton(
                text=cat,
                elevation=0,
                md_bg_color=(0.14, 0.17, 0.22, 1),
                text_color=(0.9, 0.92, 0.98, 1)
            )
            self.chips_box.add_widget(btn)
        self.chips_scroll.add_widget(self.chips_box)
        self.root_layout.add_widget(self.chips_scroll)

        # SPEED DIAL HEADER
        self.section_label = MDLabel(
            text="Speed dial",
            font_style="H6",
            bold=True,
            size_hint_y=None,
            height=dp(36),
            padding=[dp(16), 0]
        )
        self.root_layout.add_widget(self.section_label)

        # SPEED DIAL HORIZONTAL SCROLL
        self.speed_dial_scroll = MDScrollView(
            do_scroll_x=True,
            do_scroll_y=False,
            size_hint=(1, None),
            height=dp(340),
            bar_width=0
        )
        self.grid = MDGridLayout(
            rows=3,
            adaptive_width=True,
            size_hint_x=None,
            spacing=dp(10),
            padding=[dp(16), dp(4), dp(16), dp(4)]
        )
        self.speed_dial_scroll.add_widget(self.grid)
        self.root_layout.add_widget(self.speed_dial_scroll)

        # LIST VIEW
        self.main_scroll = MDScrollView(size_hint=(1, 1), bar_width=0)
        self.list_view = MDList()
        self.main_scroll.add_widget(self.list_view)
        self.root_layout.add_widget(self.main_scroll)

        # FLOATING MINI-PLAYER
        self.mini_card = ClickableCard(
            orientation="vertical",
            size_hint=(0.94, None),
            height=dp(64),
            pos_hint={'center_x': 0.5},
            radius=[dp(18)],
            md_bg_color=(0.10, 0.13, 0.18, 0.96),
            elevation=4
        )
        self.mini_progress = MDSlider(
            min=0, max=100, value=0,
            size_hint_y=None, height=dp(6),
            hint=False
        )
        self.mini_card.add_widget(self.mini_progress)

        mini_row = MDBoxLayout(
            orientation="horizontal",
            size_hint=(1, 1),
            padding=[dp(10), 0, dp(10), dp(4)],
            spacing=dp(8)
        )
        self.mini_artwork = FitImage(
            source="assets/placeholder.png",
            size_hint=(None, None),
            size=(dp(42), dp(42)),
            radius=[dp(10)],
            pos_hint={'center_y': 0.5}
        )
        self.mini_text_box = MDBoxLayout(orientation="vertical", size_hint_x=0.55, pos_hint={'center_y': 0.5})
        self.mini_title = MDLabel(text="No song playing", font_style="Subtitle2", shorten=True, shorten_from="right")
        self.mini_artist = MDLabel(text="Tap a song to play", font_style="Caption", theme_text_color="Secondary", shorten=True)
        self.mini_text_box.add_widget(self.mini_title)
        self.mini_text_box.add_widget(self.mini_artist)

        self.btn_mini_play = MDIconButton(icon="play-circle", icon_size="30sp", pos_hint={'center_y': 0.5})
        self.btn_mini_next = MDIconButton(icon="skip-next", icon_size="24sp", pos_hint={'center_y': 0.5})
        self.btn_mini_more = MDIconButton(icon="dots-vertical", icon_size="20sp", pos_hint={'center_y': 0.5})

        mini_row.add_widget(self.mini_artwork)
        mini_row.add_widget(self.mini_text_box)
        mini_row.add_widget(self.btn_mini_play)
        mini_row.add_widget(self.btn_mini_next)
        mini_row.add_widget(self.btn_mini_more)
        self.mini_card.add_widget(mini_row)

        self.root_layout.add_widget(self.mini_card)

        # BOTTOM NAVIGATION
        self.nav_bar = MDBoxLayout(
            orientation="horizontal",
            size_hint_y=None,
            height=dp(56),
            md_bg_color=(0.04, 0.05, 0.07, 1),
            padding=[dp(8), dp(4), dp(8), dp(4)]
        )
        self.nav_home = self._create_nav_item("home", "Home", active=True)
        self.nav_search = self._create_nav_item("magnify", "Search", active=False)
        self.nav_library = self._create_nav_item("playlist-music", "Library", active=False)

        self.nav_bar.add_widget(self.nav_home)
        self.nav_bar.add_widget(self.nav_search)
        self.nav_bar.add_widget(self.nav_library)
        self.root_layout.add_widget(self.nav_bar)

        self.add_widget(self.root_layout)

        # ----------------- FULL-SCREEN EXPANDED PLAYER -----------------
        self.full_player = MDBoxLayout(
            orientation="vertical",
            size_hint=(1, 1),
            pos_hint={'x': 0, 'y': -1},
            disabled=True,
            opacity=0,
            md_bg_color=(0.04, 0.06, 0.09, 1),
            padding=[dp(20), dp(16), dp(20), dp(16)],
            spacing=dp(8)
        )

        full_top = MDBoxLayout(size_hint_y=None, height=dp(48))
        self.btn_close_full = MDIconButton(icon="chevron-down", icon_size="28sp")
        full_title_box = MDBoxLayout(orientation="vertical", pos_hint={'center_y': 0.5})
        self.full_header_title = MDLabel(text="Now Playing", font_style="Caption", halign="center", theme_text_color="Secondary")
        self.full_header_sub = MDLabel(text="", font_style="Subtitle2", bold=True, halign="center", shorten=True)
        full_title_box.add_widget(self.full_header_title)
        full_title_box.add_widget(self.full_header_sub)
        self.btn_cast = MDIconButton(icon="cast")

        full_top.add_widget(self.btn_close_full)
        full_top.add_widget(full_title_box)
        full_top.add_widget(self.btn_cast)
        self.full_player.add_widget(full_top)

        art_card = MDCard(
            size_hint=(0.88, 0.44),
            pos_hint={'center_x': 0.5},
            radius=[dp(24)],
            elevation=4,
            padding=dp(8),
            md_bg_color=(0.10, 0.13, 0.18, 1)
        )
        self.full_artwork = FitImage(source="assets/placeholder.png", radius=[dp(20)])
        art_card.add_widget(self.full_artwork)
        self.full_player.add_widget(art_card)

        title_row = MDBoxLayout(size_hint_y=None, height=dp(58), spacing=dp(8))
        text_sub = MDBoxLayout(orientation="vertical", size_hint_x=0.68, pos_hint={'center_y': 0.5})
        self.full_title = MDLabel(text="Track Title", font_style="H6", bold=True, shorten=True)
        self.full_artist = MDLabel(text="Artist Name", font_style="Subtitle2", theme_text_color="Secondary", shorten=True)
        text_sub.add_widget(self.full_title)
        text_sub.add_widget(self.full_artist)

        self.btn_share_card = ClickableCard(
            size_hint=(None, None),
            size=(dp(46), dp(46)),
            radius=[dp(14)],
            md_bg_color=(0.16, 0.19, 0.26, 1),
            pos_hint={'center_y': 0.5}
        )
        self.icon_share = MDIcon(
            icon="share-variant-outline",
            font_size="22sp",
            halign="center",
            pos_hint={'center_x': 0.5, 'center_y': 0.5},
            theme_text_color="Custom",
            text_color=(0.85, 0.88, 0.98, 1)
        )
        self.btn_share_card.add_widget(self.icon_share)

        self.btn_like_card = ClickableCard(
            size_hint=(None, None),
            size=(dp(46), dp(46)),
            radius=[dp(14)],
            md_bg_color=(0.16, 0.19, 0.26, 1),
            pos_hint={'center_y': 0.5}
        )
        self.icon_like = MDIcon(
            icon="heart-outline",
            font_size="22sp",
            halign="center",
            pos_hint={'center_x': 0.5, 'center_y': 0.5},
            theme_text_color="Custom",
            text_color=(0.85, 0.88, 0.98, 1)
        )
        self.btn_like_card.add_widget(self.icon_like)

        title_row.add_widget(text_sub)
        title_row.add_widget(self.btn_share_card)
        title_row.add_widget(self.btn_like_card)
        self.full_player.add_widget(title_row)

        self.full_slider = MDSlider(min=0, max=100, value=0, size_hint_y=None, height=dp(28), hint=False)
        time_row = MDBoxLayout(size_hint_y=None, height=dp(16))
        self.time_current = MDLabel(text="0:00", font_style="Caption", size_hint_x=0.5)
        self.time_total = MDLabel(text="0:00", font_style="Caption", halign="right", size_hint_x=0.5)
        time_row.add_widget(self.time_current)
        time_row.add_widget(self.time_total)
        self.full_player.add_widget(self.full_slider)
        self.full_player.add_widget(time_row)

        # Center Controls Row
        controls_row = MDBoxLayout(
            size_hint_y=None,
            height=dp(74),
            spacing=dp(14),
            padding=[dp(10), 0, dp(10), 0]
        )

        self.btn_full_prev_card = ClickableCard(
            size_hint=(None, None),
            size=(dp(58), dp(58)),
            radius=[dp(29)],
            md_bg_color=(0.18, 0.22, 0.30, 1),
            pos_hint={'center_y': 0.5}
        )
        self.icon_full_prev = MDIcon(
            icon="skip-previous",
            font_size="28sp",
            halign="center",
            pos_hint={'center_x': 0.5, 'center_y': 0.5},
            theme_text_color="Custom",
            text_color=(0.85, 0.88, 0.98, 1)
        )
        self.btn_full_prev_card.add_widget(self.icon_full_prev)

        self.btn_full_play_capsule = ClickableCard(
            size_hint=(1, None),
            height=dp(58),
            radius=[dp(29)],
            md_bg_color=(0.74, 0.78, 0.96, 1),
            pos_hint={'center_y': 0.5},
            padding=[dp(16), 0, dp(16), 0]
        )
        cap_row = MDBoxLayout(orientation="horizontal", spacing=dp(8), pos_hint={'center_x': 0.5, 'center_y': 0.5})
        self.capsule_icon = MDIcon(
            icon="play",
            font_size="28sp",
            halign="center",
            theme_text_color="Custom",
            text_color=(0.08, 0.10, 0.15, 1),
            pos_hint={'center_y': 0.5}
        )
        self.capsule_label = MDLabel(
            text="Play",
            bold=True,
            theme_text_color="Custom",
            text_color=(0.08, 0.10, 0.15, 1),
            pos_hint={'center_y': 0.5}
        )
        cap_row.add_widget(self.capsule_icon)
        cap_row.add_widget(self.capsule_label)
        self.btn_full_play_capsule.add_widget(cap_row)

        self.btn_full_next_card = ClickableCard(
            size_hint=(None, None),
            size=(dp(58), dp(58)),
            radius=[dp(29)],
            md_bg_color=(0.18, 0.22, 0.30, 1),
            pos_hint={'center_y': 0.5}
        )
        self.icon_full_next = MDIcon(
            icon="skip-next",
            font_size="28sp",
            halign="center",
            pos_hint={'center_x': 0.5, 'center_y': 0.5},
            theme_text_color="Custom",
            text_color=(0.85, 0.88, 0.98, 1)
        )
        self.btn_full_next_card.add_widget(self.icon_full_next)

        controls_row.add_widget(self.btn_full_prev_card)
        controls_row.add_widget(self.btn_full_play_capsule)
        controls_row.add_widget(self.btn_full_next_card)
        self.full_player.add_widget(controls_row)

        # Bottom Utility Dock
        util_bar = MDBoxLayout(size_hint_y=None, height=dp(52), spacing=dp(4))
        self.btn_queue = MDIconButton(icon="playlist-play")
        self.btn_timer = MDIconButton(icon="moon-waning-crescent")
        self.btn_full_shuffle = MDIconButton(icon="shuffle-disabled")
        self.btn_equalizer = MDIconButton(icon="tune-vertical")
        self.btn_full_repeat = MDIconButton(icon="repeat-off")

        self.btn_more_circle = ClickableCard(
            size_hint=(None, None),
            size=(dp(40), dp(40)),
            radius=[dp(20)],
            md_bg_color=(0.74, 0.78, 0.96, 0.85),
            pos_hint={'center_y': 0.5}
        )
        self.icon_more = MDIcon(
            icon="dots-vertical",
            font_size="22sp",
            halign="center",
            pos_hint={'center_x': 0.5, 'center_y': 0.5},
            theme_text_color="Custom",
            text_color=(0.08, 0.10, 0.15, 1)
        )
        self.btn_more_circle.add_widget(self.icon_more)

        for b in (self.btn_queue, self.btn_timer, self.btn_full_shuffle, self.btn_equalizer, self.btn_full_repeat):
            util_bar.add_widget(b)
        util_bar.add_widget(self.btn_more_circle)
        self.full_player.add_widget(util_bar)

        self.add_widget(self.full_player)

        # ----------------- OVERLAY BOTTOM SHEET -----------------
        self.bottom_sheet = TwoStageBottomSheet()
        self.add_widget(self.bottom_sheet)

    def _create_nav_item(self, icon: str, title: str, active: bool = False):
        card = ClickableCard(
            size_hint=(0.33, 1),
            radius=[dp(18)],
            md_bg_color=(0.20, 0.24, 0.32, 1) if active else (0, 0, 0, 0),
            padding=[dp(4), dp(2)]
        )
        box = MDBoxLayout(orientation="vertical", pos_hint={'center_x': 0.5, 'center_y': 0.5}, spacing=dp(1))
        ic = MDIcon(
            icon=icon,
            font_size="22sp",
            halign="center",
            theme_text_color="Custom",
            text_color=(0.95, 0.96, 1, 1) if active else (0.55, 0.58, 0.68, 1),
            pos_hint={'center_x': 0.5}
        )
        lb = MDLabel(
            text=title,
            font_style="Caption",
            halign="center",
            theme_text_color="Custom",
            text_color=(0.95, 0.96, 1, 1) if active else (0.55, 0.58, 0.68, 1)
        )
        box.add_widget(ic)
        box.add_widget(lb)
        card.add_widget(box)
        card.ic = ic
        card.lb = lb
        return card