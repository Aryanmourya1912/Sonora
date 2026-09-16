import os
from kivy.metrics import dp
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.floatlayout import FloatLayout
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.gridlayout import MDGridLayout
from kivymd.uix.scrollview import MDScrollView
from kivymd.uix.card import MDCard
from kivymd.uix.label import MDLabel
from kivymd.uix.button import MDIconButton, MDRaisedButton
from kivymd.uix.slider import MDSlider
from kivymd.uix.textfield import MDTextField
from kivymd.uix.list import MDList
from kivymd.uix.fitimage import FitImage


class ClickableCard(ButtonBehavior, MDCard):
    """MDCard with button click and touch release events enabled."""
    pass


class SongCard(ButtonBehavior, MDCard):
    """Compact song card for the horizontal Speed Dial."""
    def __init__(self, track_data: dict, on_click_callback, **kwargs):
        super().__init__(**kwargs)
        self.track_data = track_data
        self.orientation = "vertical"
        self.size_hint = (None, None)
        self.size = (dp(105), dp(100))
        self.radius = [dp(10)]
        self.elevation = 1
        self.md_bg_color = (0.14, 0.14, 0.14, 1)
        self.padding = dp(4)
        self.spacing = dp(4)

        thumb = track_data.get('thumbnail') or "assets/placeholder.png"
        img = FitImage(
            source=thumb,
            size_hint=(1, 0.65),
            radius=[dp(8)]
        )
        self.add_widget(img)

        title = MDLabel(
            text=track_data.get('title', 'Unknown')[:16],
            font_style="Caption",
            theme_text_color="Primary",
            shorten=True,
            shorten_from="right",
            halign="center",
            size_hint_y=0.35
        )
        self.add_widget(title)

        self.bind(on_release=lambda x: on_click_callback(self.track_data))


class PlayerScreen(FloatLayout):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        # ----------------- MAIN BACKGROUND CONTAINER -----------------
        self.root_layout = MDBoxLayout(
            orientation="vertical",
            size_hint=(1, 1),
            md_bg_color=(0.07, 0.07, 0.07, 1)
        )

        # TOP BAR
        top_bar = MDBoxLayout(
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
        top_bar.add_widget(self.header_title)

        self.btn_refresh = MDIconButton(icon="refresh", theme_text_color="Primary")
        self.btn_history = MDIconButton(icon="history", theme_text_color="Primary")
        top_bar.add_widget(self.btn_refresh)
        top_bar.add_widget(self.btn_history)
        self.root_layout.add_widget(top_bar)

        # SEARCH BAR (HIDDEN ON HOME, VISIBLE ON SEARCH TAB)
        self.search_box = MDBoxLayout(
            orientation="horizontal",
            size_hint_y=None,
            height=dp(50),
            padding=[dp(16), 0, dp(16), dp(4)],
            spacing=dp(8)
        )
        self.search_input = MDTextField(
            hint_text="Search songs, artists...",
            mode="round",
            size_hint_x=0.85
        )
        self.btn_search_go = MDIconButton(icon="magnify")
        self.search_box.add_widget(self.search_input)
        self.search_box.add_widget(self.btn_search_go)

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
                md_bg_color=(0.18, 0.18, 0.18, 1),
                text_color=(0.9, 0.9, 0.9, 1)
            )
            self.chips_box.add_widget(btn)
        self.chips_scroll.add_widget(self.chips_box)
        self.root_layout.add_widget(self.chips_scroll)

        # SPEED DIAL SECTION HEADER
        self.section_label = MDLabel(
            text="Speed dial",
            font_style="H6",
            bold=True,
            size_hint_y=None,
            height=dp(36),
            padding=[dp(16), 0]
        )
        self.root_layout.add_widget(self.section_label)

        # HORIZONTAL SPEED DIAL SCROLL
        self.speed_dial_scroll = MDScrollView(
            do_scroll_x=True,
            do_scroll_y=False,
            size_hint=(1, None),
            height=dp(325),
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

        # SEARCH RESULTS / LIBRARY LIST SCROLL
        self.main_scroll = MDScrollView(size_hint=(1, 1), bar_width=0)
        self.list_view = MDList()
        self.main_scroll.add_widget(self.list_view)
        self.root_layout.add_widget(self.main_scroll)

        # COMPACT FLOATING MINI-PLAYER
        self.mini_card = MDCard(
            orientation="vertical",
            size_hint=(1, None),
            height=dp(64),
            radius=[dp(12), dp(12), 0, 0],
            md_bg_color=(0.14, 0.14, 0.14, 1),
            elevation=4
        )
        self.mini_progress = MDSlider(
            min=0, max=100, value=0,
            size_hint_y=None, height=dp(8),
            hint=False
        )
        self.mini_card.add_widget(self.mini_progress)

        mini_row = MDBoxLayout(
            orientation="horizontal",
            size_hint=(1, 1),
            padding=[dp(12), 0, dp(8), dp(4)],
            spacing=dp(8)
        )
        self.mini_artwork = FitImage(
            source="assets/placeholder.png",
            size_hint=(None, None),
            size=(dp(42), dp(42)),
            radius=[dp(6)]
        )
        self.mini_text_box = MDBoxLayout(orientation="vertical", size_hint_x=0.55)
        self.mini_title = MDLabel(
            text="No song playing",
            font_style="Subtitle2",
            shorten=True,
            shorten_from="right"
        )
        self.mini_artist = MDLabel(
            text="Tap a song to play",
            font_style="Caption",
            theme_text_color="Secondary",
            shorten=True
        )
        self.mini_text_box.add_widget(self.mini_title)
        self.mini_text_box.add_widget(self.mini_artist)

        # Fixed: Replaced user_font_size with icon_size
        self.btn_mini_play = MDIconButton(icon="play-circle", icon_size="28sp")
        self.btn_mini_next = MDIconButton(icon="skip-next", icon_size="24sp")
        self.btn_mini_more = MDIconButton(icon="dots-vertical", icon_size="20sp")

        mini_row.add_widget(self.mini_artwork)
        mini_row.add_widget(self.mini_text_box)
        mini_row.add_widget(self.btn_mini_play)
        mini_row.add_widget(self.btn_mini_next)
        mini_row.add_widget(self.btn_mini_more)
        self.mini_card.add_widget(mini_row)

        self.root_layout.add_widget(self.mini_card)

        # BOTTOM NAVIGATION BAR
        nav_bar = MDBoxLayout(
            orientation="horizontal",
            size_hint_y=None,
            height=dp(52),
            md_bg_color=(0.10, 0.10, 0.10, 1)
        )
        self.nav_home = MDIconButton(
            icon="home", size_hint_x=0.33,
            theme_text_color="Custom", text_color=(1, 1, 1, 1)
        )
        self.nav_search = MDIconButton(
            icon="magnify", size_hint_x=0.33,
            theme_text_color="Custom", text_color=(0.5, 0.5, 0.5, 1)
        )
        self.nav_library = MDIconButton(
            icon="playlist-music", size_hint_x=0.33,
            theme_text_color="Custom", text_color=(0.5, 0.5, 0.5, 1)
        )
        nav_bar.add_widget(self.nav_home)
        nav_bar.add_widget(self.nav_search)
        nav_bar.add_widget(self.nav_library)
        self.root_layout.add_widget(nav_bar)

        self.add_widget(self.root_layout)

        # ----------------- 100% FULL-SCREEN EXPANDED PLAYER -----------------
        self.full_player = MDBoxLayout(
            orientation="vertical",
            size_hint=(1, 1),
            pos_hint={'x': 0, 'y': -1},  # Starts hidden below screen
            md_bg_color=(0.10, 0.10, 0.10, 1),
            padding=[dp(20), dp(16), dp(20), dp(16)]
        )

        # DRAG HANDLE & TOP BAR
        self.top_drag_bar = MDBoxLayout(size_hint=(1, None), height=dp(10))
        self.full_player.add_widget(self.top_drag_bar)

        full_top_bar = MDBoxLayout(size_hint_y=None, height=dp(48))
        self.btn_close_full = MDIconButton(icon="chevron-down", icon_size="28sp")
        full_titles = MDBoxLayout(orientation="vertical")
        self.full_header_title = MDLabel(text="Now Playing", font_style="Caption", halign="center", theme_text_color="Secondary")
        self.full_header_sub = MDLabel(text="", font_style="Subtitle2", bold=True, halign="center", shorten=True)
        full_titles.add_widget(self.full_header_title)
        full_titles.add_widget(self.full_header_sub)
        btn_cast = MDIconButton(icon="cast")

        full_top_bar.add_widget(self.btn_close_full)
        full_top_bar.add_widget(full_titles)
        full_top_bar.add_widget(btn_cast)
        self.full_player.add_widget(full_top_bar)

        # ARTWORK
        art_card = MDCard(
            size_hint=(0.85, 0.44),
            pos_hint={'center_x': 0.5},
            radius=[dp(18)],
            elevation=4,
            padding=dp(8),
            md_bg_color=(0.15, 0.15, 0.15, 1)
        )
        self.full_artwork = FitImage(source="assets/placeholder.png", radius=[dp(14)])
        art_card.add_widget(self.full_artwork)
        self.full_player.add_widget(art_card)

        # SONG TITLE, ARTIST, HEART & SHARE
        title_box = MDBoxLayout(size_hint_y=None, height=dp(56), spacing=dp(8))
        text_sub = MDBoxLayout(orientation="vertical", size_hint_x=0.7)
        self.full_title = MDLabel(text="Track Title", font_style="H6", bold=True, shorten=True)
        self.full_artist = MDLabel(text="Artist Name", font_style="Subtitle2", theme_text_color="Secondary", shorten=True)
        text_sub.add_widget(self.full_title)
        text_sub.add_widget(self.full_artist)

        self.btn_share = MDIconButton(icon="share-variant-outline")
        self.btn_like = MDIconButton(icon="heart-outline")
        title_box.add_widget(text_sub)
        title_box.add_widget(self.btn_share)
        title_box.add_widget(self.btn_like)
        self.full_player.add_widget(title_box)

        # SCRUBBER SLIDER & TIMESTAMPS
        self.full_slider = MDSlider(min=0, max=100, value=0, size_hint_y=None, height=dp(30), hint=False)
        time_row = MDBoxLayout(size_hint_y=None, height=dp(18))
        self.time_current = MDLabel(text="0:00", font_style="Caption", size_hint_x=0.5)
        self.time_total = MDLabel(text="0:00", font_style="Caption", halign="right", size_hint_x=0.5)
        time_row.add_widget(self.time_current)
        time_row.add_widget(self.time_total)
        self.full_player.add_widget(self.full_slider)
        self.full_player.add_widget(time_row)

        # CENTER PLAYBACK CONTROLS (PILL CAPSULE)
        controls = MDBoxLayout(size_hint_y=None, height=dp(70), spacing=dp(16))
        self.btn_full_prev = MDIconButton(icon="skip-previous", icon_size="32sp", pos_hint={'center_y': 0.5})

        # Fixed: Now uses ClickableCard so on_release is supported
        self.btn_full_play_capsule = ClickableCard(
            size_hint=(None, None),
            size=(dp(130), dp(52)),
            radius=[dp(26)],
            md_bg_color=(1, 1, 1, 1),
            pos_hint={'center_y': 0.5},
            padding=dp(8)
        )
        cap_row = MDBoxLayout(orientation="horizontal", spacing=dp(6))
        self.capsule_icon = MDIconButton(icon="play", theme_text_color="Custom", text_color=(0.1, 0.1, 0.1, 1))
        self.capsule_label = MDLabel(text="Play", bold=True, theme_text_color="Custom", text_color=(0.1, 0.1, 0.1, 1))
        cap_row.add_widget(self.capsule_icon)
        cap_row.add_widget(self.capsule_label)
        self.btn_full_play_capsule.add_widget(cap_row)

        self.btn_full_next = MDIconButton(icon="skip-next", icon_size="32sp", pos_hint={'center_y': 0.5})

        controls.add_widget(self.btn_full_prev)
        controls.add_widget(self.btn_full_play_capsule)
        controls.add_widget(self.btn_full_next)
        self.full_player.add_widget(controls)

        # BOTTOM UTILITY BAR
        util_bar = MDBoxLayout(size_hint_y=None, height=dp(48))
        self.btn_queue = MDIconButton(icon="playlist-play")
        self.btn_timer = MDIconButton(icon="moon-waning-crescent")
        self.btn_full_shuffle = MDIconButton(icon="shuffle-disabled")
        self.btn_full_repeat = MDIconButton(icon="repeat-off")
        self.btn_more = MDIconButton(icon="dots-vertical")

        for b in (self.btn_queue, self.btn_timer, self.btn_full_shuffle, self.btn_full_repeat, self.btn_more):
            util_bar.add_widget(b)
        self.full_player.add_widget(util_bar)

        self.add_widget(self.full_player)