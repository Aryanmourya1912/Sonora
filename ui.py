from kivymd.uix.screen import MDScreen
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.gridlayout import MDGridLayout
from kivymd.uix.scrollview import MDScrollView
from kivymd.uix.label import MDLabel
from kivymd.uix.button import MDIconButton, MDRaisedButton
from kivymd.uix.card import MDCard
from kivymd.uix.slider import MDSlider
from kivymd.uix.textfield import MDTextField
from kivymd.uix.list import MDList
from kivymd.uix.fitimage import FitImage
from kivy.metrics import dp

class SongCard(MDCard):
    def __init__(self, track_data: dict, on_click_callback, **kwargs):
        super().__init__(**kwargs)
        self.orientation = "vertical"
        self.size_hint = (None, None)
        self.size = (dp(105), dp(135))
        self.radius = [12, 12, 12, 12]
        self.md_bg_color = (0, 0, 0, 0)
        self.ripple_behavior = True
        self.track_data = track_data

        self.image = FitImage(
            size_hint=(None, None),
            size=(dp(105), dp(105)),
            radius=[12, 12, 12, 12],
            source=track_data.get('thumbnail') or "assets/placeholder.png"
        )
        self.add_widget(self.image)

        title_text = track_data.get('title', 'Unknown')
        self.label = MDLabel(
            text=title_text[:14] + ("..." if len(title_text) > 14 else ""),
            font_style="Caption",
            bold=True,
            halign="left",
            theme_text_color="Primary",
            size_hint_y=None,
            height=dp(26)
        )
        self.add_widget(self.label)
        self.bind(on_release=lambda x: on_click_callback(self.track_data))

class PlayerScreen(MDScreen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.md_bg_color = (0.04, 0.04, 0.04, 1)

        # ----------------- BASE HOME VIEW -----------------
        self.root_layout = MDBoxLayout(orientation='vertical', padding=[14, 10, 14, 6], spacing=8)

        # 1. Top Header (Single clean header with Refresh & History)
        header = MDBoxLayout(size_hint_y=None, height=dp(44), spacing=6)
        self.header_title = MDLabel(
            text="Home",
            font_style="H5",
            bold=True,
            theme_text_color="Custom",
            text_color=(0.95, 0.95, 0.95, 1)
        )
        header.add_widget(self.header_title)

        self.btn_refresh = MDIconButton(
            icon="refresh",
            theme_text_color="Custom",
            text_color=(0.85, 0.85, 0.85, 1)
        )
        header.add_widget(self.btn_refresh)

        self.btn_history = MDIconButton(
            icon="history",
            theme_text_color="Custom",
            text_color=(0.85, 0.85, 0.85, 1)
        )
        header.add_widget(self.btn_history)
        header.add_widget(MDIconButton(icon="account-circle-outline", theme_text_color="Custom", text_color=(0.8, 0.8, 0.8, 1)))
        self.root_layout.add_widget(header)

        # 2. Category Filter Pills
        self.chips_scroll = MDScrollView(size_hint_y=None, height=dp(36), do_scroll_x=True, do_scroll_y=False)
        self.chips_box = MDBoxLayout(orientation='horizontal', spacing=8, adaptive_width=True)
        for cat in ["Trending", "Podcasts", "Workout", "Feel good", "Energy", "Relax"]:
            btn = MDRaisedButton(
                text=cat,
                elevation=0,
                md_bg_color=(0.14, 0.14, 0.14, 1),
                text_color=(0.9, 0.9, 0.9, 1),
                size_hint=(None, None),
                height=dp(32)
            )
            self.chips_box.add_widget(btn)
        self.chips_scroll.add_widget(self.chips_box)
        self.root_layout.add_widget(self.chips_scroll)

        # 3. Main Body Scroll (Speed Dial & Lists)
        self.body_scroll = MDScrollView(size_hint_y=0.62)
        self.body_layout = MDBoxLayout(orientation='vertical', adaptive_height=True, spacing=14)

        self.section_label = MDLabel(
            text="Speed dial",
            font_style="H6",
            bold=True,
            theme_text_color="Custom",
            text_color=(0.92, 0.82, 0.60, 1),
            size_hint_y=None,
            height=dp(30)
        )
        self.body_layout.add_widget(self.section_label)

        self.grid = MDGridLayout(cols=3, spacing=[14, 14], adaptive_height=True, pos_hint={"center_x": 0.5})
        self.body_layout.add_widget(self.grid)

        self.list_view = MDList()
        self.body_layout.add_widget(self.list_view)
        self.body_scroll.add_widget(self.body_layout)
        self.root_layout.add_widget(self.body_scroll)

        # Search Bar
        self.search_box = MDBoxLayout(size_hint_y=None, height=dp(50), spacing=8)
        self.search_input = MDTextField(hint_text="Search song, artist, album...", multiline=False, size_hint_x=0.85)
        self.btn_search_go = MDIconButton(icon="magnify", pos_hint={"center_y": 0.5})
        self.search_box.add_widget(self.search_input)
        self.search_box.add_widget(self.btn_search_go)

        # 4. Floating Bottom Mini-Player
        self.mini_player = MDCard(
            orientation="vertical",
            size_hint=(1, None),
            height=dp(66),
            radius=[16, 16, 16, 16],
            md_bg_color=(0.14, 0.14, 0.12, 1),
            padding=[8, 2, 8, 4],
            spacing=2
        )

        self.mini_progress = MDSlider(min=0, max=100, value=0, size_hint_y=None, height=dp(12), hint=False)
        self.mini_player.add_widget(self.mini_progress)

        controls_row = MDBoxLayout(orientation='horizontal', spacing=6, size_hint_y=None, height=dp(46))
        self.mini_artwork = FitImage(
            size_hint=(None, None),
            size=(dp(42), dp(42)),
            radius=[8, 8, 8, 8],
            source="assets/placeholder.png",
            pos_hint={"center_y": 0.5}
        )
        controls_row.add_widget(self.mini_artwork)

        self.mini_text_box = MDBoxLayout(orientation='vertical', spacing=1, pos_hint={"center_y": 0.5})
        self.mini_title = MDLabel(text="No Song Playing", font_style="Subtitle2", bold=True, shorten=True, height=dp(20))
        self.mini_artist = MDLabel(text="Tap a track to play", font_style="Caption", theme_text_color="Secondary", shorten=True, height=dp(16))
        self.mini_text_box.add_widget(self.mini_title)
        self.mini_text_box.add_widget(self.mini_artist)
        controls_row.add_widget(self.mini_text_box)

        self.btn_mini_play = MDIconButton(icon="play-circle", icon_size="34sp")
        self.btn_mini_next = MDIconButton(icon="skip-next")
        self.btn_mini_more = MDIconButton(
            icon="dots-vertical",
            theme_text_color="Custom",
            text_color=(0.85, 0.85, 0.85, 1)
        )
        controls_row.add_widget(self.btn_mini_play)
        controls_row.add_widget(self.btn_mini_next)
        controls_row.add_widget(self.btn_mini_more)

        self.mini_player.add_widget(controls_row)
        self.root_layout.add_widget(self.mini_player)

        # 5. Bottom Navigation Bar
        bottom_nav = MDBoxLayout(size_hint_y=None, height=dp(48), spacing=6)
        self.nav_home = MDIconButton(icon="home", size_hint_x=0.33, theme_text_color="Custom", text_color=(1, 1, 1, 1))
        self.nav_search = MDIconButton(icon="magnify", size_hint_x=0.33, theme_text_color="Custom", text_color=(0.5, 0.5, 0.5, 1))
        self.nav_library = MDIconButton(icon="bookmark-music-outline", size_hint_x=0.33, theme_text_color="Custom", text_color=(0.5, 0.5, 0.5, 1))
        bottom_nav.add_widget(self.nav_home)
        bottom_nav.add_widget(self.nav_search)
        bottom_nav.add_widget(self.nav_library)
        self.root_layout.add_widget(bottom_nav)

        self.add_widget(self.root_layout)

        # ----------------- FULL SCREEN SLIDE-UP MODAL -----------------
        self.full_player = MDBoxLayout(
            orientation='vertical',
            padding=[dp(18), dp(8), dp(18), dp(12)],
            spacing=dp(10),
            size_hint=(1, 1),
            pos_hint={'y': -1},
            md_bg_color=(0.14, 0.13, 0.08, 1)
        )

        # Top Drag Handle
        self.top_drag_bar = MDCard(
            size_hint=(None, None),
            size=(dp(48), dp(5)),
            radius=[3, 3, 3, 3],
            md_bg_color=(0.5, 0.5, 0.5, 0.6),
            pos_hint={"center_x": 0.5},
            ripple_behavior=True
        )
        self.full_player.add_widget(self.top_drag_bar)

        # Top Bar: Down Chevron & Title
        top_bar = MDBoxLayout(size_hint_y=None, height=dp(44), spacing=8)
        self.btn_close_full = MDIconButton(
            icon="chevron-down",
            icon_size="34sp",
            theme_text_color="Custom",
            text_color=(1, 1, 1, 1),
            md_bg_color=(0.24, 0.23, 0.16, 1),
            pos_hint={"center_y": 0.5}
        )
        top_text_box = MDBoxLayout(orientation='vertical', spacing=1, pos_hint={"center_y": 0.5})
        self.full_header_title = MDLabel(text="Now Playing", font_style="Caption", bold=True, theme_text_color="Secondary", halign="center")
        self.full_header_sub = MDLabel(text="Queue Mix", font_style="Subtitle2", bold=True, halign="center")
        top_text_box.add_widget(self.full_header_title)
        top_text_box.add_widget(self.full_header_sub)

        top_bar.add_widget(self.btn_close_full)
        top_bar.add_widget(top_text_box)
        top_bar.add_widget(MDIconButton(icon="cast", theme_text_color="Custom", text_color=(1, 1, 1, 1), pos_hint={"center_y": 0.5}))
        self.full_player.add_widget(top_bar)

        # Album Art Card
        self.full_artwork_container = MDCard(
            size_hint=(None, None),
            size=(dp(240), dp(240)),
            radius=[16, 16, 16, 16],
            pos_hint={"center_x": 0.5},
            elevation=4
        )
        self.full_artwork = FitImage(radius=[16, 16, 16, 16], source="assets/placeholder.png")
        self.full_artwork_container.add_widget(self.full_artwork)
        self.full_player.add_widget(self.full_artwork_container)

        # Title & Artist Row with Share/Heart Pills
        info_row = MDBoxLayout(size_hint_y=None, height=dp(48), spacing=8)
        title_artist_box = MDBoxLayout(orientation='vertical', spacing=1, size_hint_x=0.74, pos_hint={"center_y": 0.5})
        self.full_title = MDLabel(text="No Song Playing", font_style="Subtitle1", bold=True, shorten=True, height=dp(24))
        self.full_artist = MDLabel(text="Select a track", font_style="Caption", theme_text_color="Secondary", shorten=True, height=dp(18))
        title_artist_box.add_widget(self.full_title)
        title_artist_box.add_widget(self.full_artist)
        info_row.add_widget(title_artist_box)

        self.btn_share = MDIconButton(
            icon="share-variant-outline",
            theme_text_color="Custom",
            text_color=(1, 1, 1, 1),
            md_bg_color=(0.22, 0.21, 0.15, 1),
            pos_hint={"center_y": 0.5}
        )
        self.btn_like = MDIconButton(
            icon="heart-outline",
            theme_text_color="Custom",
            text_color=(1, 1, 1, 1),
            md_bg_color=(0.22, 0.21, 0.15, 1),
            pos_hint={"center_y": 0.5}
        )
        info_row.add_widget(self.btn_share)
        info_row.add_widget(self.btn_like)
        self.full_player.add_widget(info_row)

        # Scrubber Slider
        self.full_slider = MDSlider(min=0, max=100, value=0, size_hint_y=None, height=dp(26), hint=False)
        self.full_player.add_widget(self.full_slider)

        # Timeline Timestamps
        time_row = MDBoxLayout(size_hint_y=None, height=dp(16))
        self.time_current = MDLabel(text="0:00", font_style="Caption", theme_text_color="Secondary", halign="left")
        self.time_total = MDLabel(text="0:00", font_style="Caption", theme_text_color="Secondary", halign="right")
        time_row.add_widget(self.time_current)
        time_row.add_widget(self.time_total)
        self.full_player.add_widget(time_row)

        # Main Playback Controls
        ctrl_box = MDBoxLayout(size_hint_y=None, height=dp(64), spacing=18, pos_hint={"center_x": 0.5}, adaptive_width=True)

        self.btn_full_prev = MDIconButton(
            icon="skip-previous",
            icon_size="30sp",
            md_bg_color=(0.25, 0.24, 0.17, 1),
            theme_text_color="Custom",
            text_color=(1, 1, 1, 1),
            size_hint=(None, None),
            size=(dp(50), dp(50)),
            pos_hint={"center_y": 0.5}
        )

        self.btn_full_play_capsule = MDCard(
            size_hint=(None, None),
            size=(dp(130), dp(50)),
            radius=[25, 25, 25, 25],
            md_bg_color=(0.95, 0.95, 0.95, 1),
            padding=[14, 0, 14, 0],
            pos_hint={"center_y": 0.5},
            ripple_behavior=True
        )
        capsule_layout = MDBoxLayout(spacing=6, pos_hint={"center_x": 0.5, "center_y": 0.5})
        self.capsule_icon = MDIconButton(icon="play", theme_text_color="Custom", text_color=(0.1, 0.1, 0.1, 1), pos_hint={"center_y": 0.5})
        self.capsule_label = MDLabel(text="Play", bold=True, theme_text_color="Custom", text_color=(0.1, 0.1, 0.1, 1), pos_hint={"center_y": 0.5})
        capsule_layout.add_widget(self.capsule_icon)
        capsule_layout.add_widget(self.capsule_label)
        self.btn_full_play_capsule.add_widget(capsule_layout)

        self.btn_full_next = MDIconButton(
            icon="skip-next",
            icon_size="30sp",
            md_bg_color=(0.25, 0.24, 0.17, 1),
            theme_text_color="Custom",
            text_color=(1, 1, 1, 1),
            size_hint=(None, None),
            size=(dp(50), dp(50)),
            pos_hint={"center_y": 0.5}
        )

        ctrl_box.add_widget(self.btn_full_prev)
        ctrl_box.add_widget(self.btn_full_play_capsule)
        ctrl_box.add_widget(self.btn_full_next)
        self.full_player.add_widget(ctrl_box)

        # Bottom Utility Bar (Fourth button [btn_eq] removed)
        utility_bar = MDBoxLayout(size_hint_y=None, height=dp(42), spacing=14, pos_hint={"center_x": 0.5}, adaptive_width=True)
        self.btn_queue = MDIconButton(icon="playlist-music", theme_text_color="Custom", text_color=(0.8, 0.8, 0.8, 1))
        self.btn_timer = MDIconButton(icon="moon-waning-crescent", theme_text_color="Custom", text_color=(0.8, 0.8, 0.8, 1))
        self.btn_full_shuffle = MDIconButton(icon="shuffle-disabled", theme_text_color="Custom", text_color=(0.5, 0.5, 0.5, 1))
        self.btn_full_repeat = MDIconButton(icon="repeat-off", theme_text_color="Custom", text_color=(0.5, 0.5, 0.5, 1))
        self.btn_more = MDIconButton(icon="dots-vertical", theme_text_color="Custom", text_color=(0.8, 0.8, 0.8, 1))

        for btn in (self.btn_queue, self.btn_timer, self.btn_full_shuffle, self.btn_full_repeat, self.btn_more):
            utility_bar.add_widget(btn)

        self.full_player.add_widget(utility_bar)
        self.add_widget(self.full_player)