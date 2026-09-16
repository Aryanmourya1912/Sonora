import os
import random
import re
from typing import Optional

import mutagen
import yt_dlp
from kivy.utils import platform


class SafeLogger:
    """Suppress normal yt-dlp output and display errors only."""

    def debug(self, msg):
        pass

    def info(self, msg):
        pass

    def warning(self, msg):
        pass

    def error(self, msg):
        print(f"[yt-dlp error] {msg}")


class SearchEngine:
    """
    YouTube search, music discovery, recommendations,
    audio downloading, and local caching.
    """

    def __init__(self, cache_dir: Optional[str] = None):

        self.logger = SafeLogger()

        # ---------------------------------------------------------
        # 1. Resolve writable cache directory
        # ---------------------------------------------------------

        if cache_dir:
            self.cache_dir = os.path.abspath(cache_dir)

        elif platform == "android":
            try:
                from kivymd.app import MDApp

                app = MDApp.get_running_app()

                if app:
                    base_dir = app.user_data_dir
                else:
                    base_dir = os.path.expanduser("~")

                self.cache_dir = os.path.join(
                    base_dir,
                    "audio_cache",
                )

            except Exception as error:
                print(f"[Android Cache Path Error] {error}")
                self.cache_dir = os.path.abspath("audio_cache")

        else:
            self.cache_dir = os.path.abspath("audio_cache")

        # Create cache directory
        try:
            os.makedirs(
                self.cache_dir,
                exist_ok=True,
            )
        except OSError as error:
            print(f"[SearchEngine Cache Dir Error] {error}")

        # ---------------------------------------------------------
        # 2. Base yt-dlp options
        # ---------------------------------------------------------

        self.base_opts = {
            "quiet": True,
            "no_warnings": True,
            "logger": self.logger,
            "nocheckcertificate": True,

            # Disable yt-dlp's own cache.
            # Our application has its own audio cache.
            "cachedir": False,
        }

        # ---------------------------------------------------------
        # 3. Discovery search queries
        # ---------------------------------------------------------

        self.discovery_queries = [

            # 🇮🇳 Indian Trending Music
            "Viral Instagram songs India",
            "Trending Indian songs 2026",
            "Latest Indian viral songs",
            "Top Indian Spotify hits",
            "Indian YouTube trending songs",
            "Instagram viral songs Hindi",

            # 🎵 Hindi / Bollywood
            "Hindi Hits",
            "Latest Bollywood hits",
            "Bollywood party songs",
            "Best Hindi songs playlist",
            "New Hindi romantic songs",
            "Hindi lo-fi songs",
            "Hindi sad songs",
            "Hindi indie songs",
            "Hindi acoustic songs",

            # 🕉️ Bhakti / Devotional
            "Bhakti Hits",
            "Latest Hindi devotional songs",
            "Hanuman bhajan hits",
            "Shiv bhajan popular songs",
            "Krishna bhajan hits",
            "Ram bhajan trending songs",
            "Mahadev devotional songs",

            # 🎤 Punjabi
            "Punjabi Hits songs",
            "Latest Punjabi songs",
            "Punjabi viral songs",
            "Punjabi party songs",
            "Punjabi romantic songs",
            "Punjabi hip hop songs",
            "Punjabi lo-fi songs",

            # 🎧 Phonk / Electronic
            "Viral Instagram phonk",
            "Indian phonk songs",
            "Hindi phonk remix",
            "Trending phonk music",
            "Indian EDM hits",
            "Indian trap music",
            "Viral bass boosted songs",

            # 🌎 International
            "Top global viral hits songs",
            "Popular English songs in India",
            "International Instagram viral songs",
            "Global Spotify viral hits",
            "Trending English pop songs",
            "Top global EDM hits",

            # 🎼 Regional Indian
            "Latest Marathi hit songs",
            "Marathi viral songs",
            "South Indian trending songs",
            "Tamil hit songs",
            "Telugu hit songs",
            "Malayalam hit songs",
            "Bengali hit songs",
            "Haryanvi viral songs",
            "Bhojpuri hit songs",

            # 🌙 Mood based
            "Relaxing Hindi songs",
            "Hindi chill playlist",
            "Indian night drive songs",
            "Hindi workout songs",
            "Indian study music",
            "Hindi heartbreak songs",
            "Indian rain songs",
        ]

    # =============================================================
    # INTERNAL HELPERS
    # =============================================================

    def _placeholder_path(self) -> str:
        """
        Return an absolute path to the placeholder image.
        """

        base_dir = os.path.dirname(
            os.path.abspath(__file__)
        )

        return os.path.join(
            base_dir,
            "assets",
            "placeholder.png",
        )

    def _get_thumbnail(self, entry: dict) -> str:
        """
        Safely extract a thumbnail URL from a yt-dlp entry.
        """

        thumbnail = entry.get("thumbnail")

        if thumbnail:
            return thumbnail

        thumbnails = entry.get("thumbnails") or []

        # Search from highest-quality/latest entries first
        for item in reversed(thumbnails):
            if not item:
                continue

            url = item.get("url")

            if url:
                return url

        return self._placeholder_path()

    def _build_track_dict(
        self,
        entry: dict,
        default_uploader: str = "Unknown Artist",
    ) -> Optional[dict]:
        """
        Convert a yt-dlp entry into the application's
        standard track dictionary.
        """

        if not entry:
            return None

        video_id = entry.get("id")

        if not video_id:
            return None

        title = entry.get("title") or "Unknown Track"

        uploader = (
            entry.get("uploader")
            or entry.get("channel")
            or default_uploader
        )

        webpage_url = (
            entry.get("webpage_url")
            or entry.get("original_url")
            or f"https://www.youtube.com/watch?v={video_id}"
        )

        return {
            "id": video_id,
            "title": title,
            "uploader": uploader,
            "duration": entry.get("duration") or 0,
            "thumbnail": self._get_thumbnail(entry),
            "webpage_url": webpage_url,
        }

    # =============================================================
    # 1. CLEAN SONG TITLE
    # =============================================================

    def _extract_clean_title(
        self,
        full_title: str,
        artist: str = "",
    ) -> str:
        """
        Convert a YouTube title into a simplified title
        for duplicate/variant detection.
        """

        if not full_title:
            return ""

        cleaned = full_title.strip()

        # ---------------------------------------------------------
        # Remove square bracket sections
        #
        # Example:
        # Song Name [Official Video]
        # -> Song Name
        # ---------------------------------------------------------

        cleaned = re.sub(
            r"\[[^\]]*\]",
            "",
            cleaned,
        )

        # ---------------------------------------------------------
        # Remove parentheses
        #
        # Example:
        # Song Name (Official Audio)
        # -> Song Name
        # ---------------------------------------------------------

        cleaned = re.sub(
            r"\([^)]*\)",
            "",
            cleaned,
        )

        # ---------------------------------------------------------
        # Remove artist prefix when it matches the uploader
        #
        # Example:
        # Arijit Singh - Kesariya
        # -> Kesariya
        # ---------------------------------------------------------

        if artist and " - " in cleaned:

            first_part, second_part = cleaned.split(
                " - ",
                1,
            )

            if first_part.strip().lower() in artist.lower():
                cleaned = second_part

        # ---------------------------------------------------------
        # Remove common YouTube noise
        # ---------------------------------------------------------

        noise_pattern = re.compile(
            r"\b("
            r"official\s+video|"
            r"official\s+audio|"
            r"official|"
            r"music\s+video|"
            r"lyric\s+video|"
            r"lyrics|"
            r"audio|"
            r"visualizer|"
            r"remix|"
            r"slowed|"
            r"reverb|"
            r"bass\s+boosted|"
            r"live|"
            r"hd|"
            r"4k|"
            r"remastered|"
            r"extended"
            r")\b",
            re.IGNORECASE,
        )

        cleaned = noise_pattern.sub(
            "",
            cleaned,
        )

        # ---------------------------------------------------------
        # Remove punctuation
        # ---------------------------------------------------------

        cleaned = re.sub(
            r"[^\w\s]",
            "",
            cleaned,
        )

        # ---------------------------------------------------------
        # Normalize whitespace
        # ---------------------------------------------------------

        cleaned = re.sub(
            r"\s+",
            " ",
            cleaned,
        ).strip()

        return cleaned.lower()

    # =============================================================
    # 2. CHECK FOR SAME SONG OR VARIANT
    # =============================================================

    def _is_same_or_variant(
        self,
        candidate_title: str,
        clean_seed_title: str,
    ) -> bool:
        """
        Determine whether a candidate is probably the same
        song or a close variant of the seed song.
        """

        candidate_clean = self._extract_clean_title(
            candidate_title
        )

        if not clean_seed_title or not candidate_clean:
            return False

        # Exact match
        if candidate_clean == clean_seed_title:
            return True

        # One title completely contains the other
        if (
            clean_seed_title in candidate_clean
            or candidate_clean in clean_seed_title
        ):
            return True

        # Word-based comparison
        seed_words = {
            word
            for word in clean_seed_title.split()
            if len(word) > 2
        }

        candidate_words = set(
            candidate_clean.split()
        )

        if seed_words and seed_words.issubset(
            candidate_words
        ):
            return True

        return False

    # =============================================================
    # 3. SEARCH YOUTUBE
    # =============================================================

    def search_tracks(
        self,
        query: str,
        max_results: int = 9,
    ) -> list[dict]:
        """
        Search YouTube and return normalized track dictionaries.
        """

        if not query or not query.strip():
            return []

        # Prevent invalid values
        max_results = max(
            1,
            min(int(max_results), 50),
        )

        options = {
            **self.base_opts,

            # Return metadata without downloading
            "extract_flat": True,
            "skip_download": True,
        }

        results = []

        try:

            with yt_dlp.YoutubeDL(options) as ydl:

                search_url = (
                    f"ytsearch{max_results}:"
                    f"{query.strip()}"
                )

                info = ydl.extract_info(
                    search_url,
                    download=False,
                )

                if not info:
                    return []

                for entry in info.get("entries", []):

                    track = self._build_track_dict(
                        entry
                    )

                    if track:
                        results.append(track)

        except Exception as error:

            print(
                f"[Search Error] {error}"
            )

        return results

    # =============================================================
    # 4. RANDOM MUSIC DISCOVERY
    # =============================================================

    def get_trending_tracks(
        self,
        count: int = 9,
    ) -> list[dict]:
        """
        Return randomly discovered music.

        Note:
        This searches discovery queries; it does not directly
        query YouTube's official Trending Music chart.
        """

        if count <= 0:
            return []

        random_seed = random.choice(
            self.discovery_queries
        )

        return self.search_tracks(
            random_seed,
            max_results=count,
        )

    # =============================================================
    # 5. GET SIMILAR TRACKS
    # =============================================================

    def get_similar_tracks(
        self,
        current_track: dict,
        count: int = 8,
    ) -> list[dict]:
        """
        Find tracks similar to the currently playing track.

        Method 1:
            YouTube Radio Mix

        Method 2:
            Artist/uploader fallback search
        """

        if not current_track or count <= 0:
            return []

        video_id = current_track.get(
            "id",
            "",
        )

        raw_title = current_track.get(
            "title",
            "",
        )

        artist = current_track.get(
            "uploader",
            "",
        )

        clean_seed_title = (
            self._extract_clean_title(
                raw_title,
                artist,
            )
        )

        results = []

        # =========================================================
        # METHOD 1: YOUTUBE RADIO MIX
        # =========================================================

        if video_id:

            mix_url = (
                "https://www.youtube.com/watch?"
                f"v={video_id}&list=RD{video_id}"
            )

            options = {
                **self.base_opts,

                "extract_flat": True,

                # Request extra results because some may be
                # duplicates or unusable entries.
                "playlist_items": f"1-{count + 15}",

                "skip_download": True,
            }

            try:

                with yt_dlp.YoutubeDL(options) as ydl:

                    info = ydl.extract_info(
                        mix_url,
                        download=False,
                    )

                    if info:

                        for entry in info.get(
                            "entries",
                            [],
                        ):

                            if not entry:
                                continue

                            candidate_id = entry.get(
                                "id"
                            )

                            candidate_title = (
                                entry.get(
                                    "title",
                                    "",
                                )
                            )

                            # Skip current track
                            if (
                                not candidate_id
                                or candidate_id == video_id
                            ):
                                continue

                            # Skip same song / variants
                            if self._is_same_or_variant(
                                candidate_title,
                                clean_seed_title,
                            ):
                                continue

                            candidate = (
                                self._build_track_dict(
                                    entry,
                                    default_uploader=(
                                        "Various Artists"
                                    ),
                                )
                            )

                            if not candidate:
                                continue

                            # Prevent duplicate IDs
                            if any(
                                item.get("id")
                                == candidate_id
                                for item in results
                            ):
                                continue

                            results.append(candidate)

                            if len(results) >= count:
                                break

            except Exception as error:

                print(
                    f"[Radio Mix Fetch Notice] "
                    f"{error}"
                )

        # =========================================================
        # METHOD 2: FALLBACK SEARCH
        # =========================================================

        if len(results) < count and artist:

            fallback_query = (
                f"{artist} radio mix "
                f"playlist top tracks"
            )

            candidates = self.search_tracks(
                fallback_query,
                max_results=25,
            )

            for candidate in candidates:

                candidate_id = candidate.get(
                    "id"
                )

                candidate_title = candidate.get(
                    "title",
                    "",
                )

                # Skip current song
                if candidate_id == video_id:
                    continue

                # Skip same song / variants
                if self._is_same_or_variant(
                    candidate_title,
                    clean_seed_title,
                ):
                    continue

                # Skip duplicate IDs
                if any(
                    item.get("id") == candidate_id
                    for item in results
                ):
                    continue

                # Skip songs that look like variants
                # of songs already recommended
                is_duplicate_variant = any(
                    self._is_same_or_variant(
                        candidate_title,
                        self._extract_clean_title(
                            item.get("title", "")
                        ),
                    )
                    for item in results
                )

                if is_duplicate_variant:
                    continue

                results.append(candidate)

                if len(results) >= count:
                    break

        return results

    # =============================================================
    # 6. READ AUDIO DURATION
    # =============================================================

    def _get_audio_duration(
        self,
        filepath: str,
    ) -> float:
        """
        Read duration from an existing audio file.
        """

        try:

            media_file = mutagen.File(
                filepath
            )

            if (
                media_file
                and media_file.info
                and hasattr(
                    media_file.info,
                    "length",
                )
            ):
                return float(
                    media_file.info.length
                )

        except Exception:
            pass

        return 0.0

    # =============================================================
    # 7. FIND CACHED AUDIO FILE
    # =============================================================

    def _find_cached_file(
        self,
        track_id: str,
    ) -> Optional[str]:
        """
        Look for an already downloaded audio file.
        """

        supported_extensions = (
            "m4a",
            "mp3",
            "ogg",
            "opus",
            "webm",
        )

        for ext in supported_extensions:

            candidate = os.path.abspath(
                os.path.join(
                    self.cache_dir,
                    f"{track_id}.{ext}",
                )
            )

            if not os.path.isfile(candidate):
                continue

            try:
                if os.path.getsize(candidate) <= 1024:
                    continue
            except OSError:
                continue

            return candidate

        return None

    # =============================================================
    # 8. DOWNLOAD AND PREPARE AUDIO
    # =============================================================

    def prepare_audio_file(
        self,
        video_url: str,
        track_id: str,
    ) -> tuple[Optional[str], float]:
        """
        Download audio if it is not already cached.

        Returns:
            (file_path, duration)

        If unsuccessful:
            (None, 0.0)
        """

        if not track_id:
            return None, 0.0

        # ---------------------------------------------------------
        # Create YouTube URL if only ID was provided
        # ---------------------------------------------------------

        if not video_url:
            video_url = (
                "https://www.youtube.com/watch?v="
                f"{track_id}"
            )

        # ---------------------------------------------------------
        # STEP 1: Check local cache
        # ---------------------------------------------------------

        cached_file = self._find_cached_file(
            track_id
        )

        if cached_file:

            duration = (
                self._get_audio_duration(
                    cached_file
                )
            )

            return cached_file, duration

        # ---------------------------------------------------------
        # STEP 2: Download
        # ---------------------------------------------------------

        output_template = os.path.join(
            self.cache_dir,
            f"{track_id}.%(ext)s",
        )

        options = {
            **self.base_opts,

            # Prefer M4A, otherwise let yt-dlp select
            # the best available audio.
            "format": (
                "bestaudio[ext=m4a]"
                "/bestaudio/best"
            ),

            "outtmpl": output_template,

            "noplaylist": True,
        }

        duration = 0.0

        try:

            with yt_dlp.YoutubeDL(
                options
            ) as ydl:

                info = ydl.extract_info(
                    video_url,
                    download=True,
                )

                if info:

                    raw_duration = info.get(
                        "duration"
                    )

                    if raw_duration:
                        duration = float(
                            raw_duration
                        )

        except Exception as error:

            print(
                f"[Download Error] {error}"
            )

            return None, 0.0

        # ---------------------------------------------------------
        # STEP 3: Locate downloaded file
        # ---------------------------------------------------------

        final_file = (
            self._find_cached_file(
                track_id
            )
        )

        if not final_file:
            return None, 0.0

        # ---------------------------------------------------------
        # STEP 4: Read duration from file if necessary
        # ---------------------------------------------------------

        if duration <= 0:

            duration = (
                self._get_audio_duration(
                    final_file
                )
            )

        return final_file, duration