import os
import random
import re

import mutagen
import yt_dlp


class SafeLogger:
    """Suppress most yt-dlp messages and display errors only."""

    def debug(self, msg):
        pass

    def info(self, msg):
        pass

    def warning(self, msg):
        pass

    def error(self, msg):
        print(f"[yt-dlp error] {msg}")


class SearchEngine:
    """YouTube search, music discovery, recommendations, and caching."""

    def __init__(self, cache_dir: str = "cache"):
        self.logger = SafeLogger()
        self.cache_dir = cache_dir

        # Create the cache directory if it does not exist.
        os.makedirs(self.cache_dir, exist_ok=True)

        # Common yt-dlp options.
        self.base_opts = {
            "quiet": True,
            "no_warnings": True,
            "logger": self.logger,
            "nocheckcertificate": True,
        }

        # Search queries used for random music discovery.
        self.discovery_queries = [
            # 🇮🇳 Indian Trending Music
            "Viral Instagram songs India",
            "Trending Indian songs 2026",
            "Latest Indian viral songs",
            "Top Indian Spotify hits",
            "Indian YouTube trending songs",
            "Instagram viral songs Hindi",

            # 🎵 Hindi and Bollywood
            "Hindi Hits",
            "Latest Bollywood hits",
            "Bollywood party songs",
            "Best Hindi songs playlist",
            "New Hindi romantic songs",
            "Hindi lo-fi songs",
            "Hindi sad songs",
            "Hindi indie songs",
            "Hindi acoustic songs",

            # 🕉️ Bhakti and Devotional
            "Bhakti Hits",
            "Latest Hindi devotional songs",
            "Hanuman bhajan hits",
            "Shiv bhajan popular songs",
            "Krishna bhajan hits",
            "Ram bhajan trending songs",
            "Mahadev devotional songs",

            # 🎤 Punjabi Music
            "Punjabi Hits songs",
            "Latest Punjabi songs",
            "Punjabi viral songs",
            "Punjabi party songs",
            "Punjabi romantic songs",
            "Punjabi hip hop songs",
            "Punjabi lo-fi songs",

            # 🎧 Phonk and Electronic
            "Viral Instagram phonk",
            "Indian phonk songs",
            "Hindi phonk remix",
            "Trending phonk music",
            "Indian EDM hits",
            "Indian trap music",
            "Viral bass boosted songs",

            # 🌎 International Music Popular in India
            "Top global viral hits songs",
            "Popular English songs in India",
            "International Instagram viral songs",
            "Global Spotify viral hits",
            "Trending English pop songs",
            "Top global EDM hits",

            # 🎼 Regional Indian Music
            "Latest Marathi hit songs",
            "Marathi viral songs",
            "South Indian trending songs",
            "Tamil hit songs",
            "Telugu hit songs",
            "Malayalam hit songs",
            "Bengali hit songs",
            "Haryanvi viral songs",
            "Bhojpuri hit songs",

            # 🌙 Mood-based Discovery
            "Relaxing Hindi songs",
            "Hindi chill playlist",
            "Indian night drive songs",
            "Hindi workout songs",
            "Indian study music",
            "Hindi heartbreak songs",
            "Indian rain songs",
        ]

    # =========================================================
    # 1. CLEAN SONG TITLE
    # =========================================================

    def _extract_clean_title(
        self,
        full_title: str,
        artist: str = "",
    ) -> str:
        """
        Simplify a YouTube song title.

        Removes:
        - Bracketed descriptions
        - Parenthesized descriptions
        - Artist names before separators
        - Common video metadata
        - Special characters
        """

        if not full_title:
            return ""

        cleaned = full_title.strip()

        # Remove square-bracket content.
        # Example: Song Name [Official Video]
        cleaned = re.sub(r"\[[^\]]*\]", "", cleaned)

        # Remove parentheses content.
        # Example: Song Name (Lyrics)
        cleaned = re.sub(r"\([^)]*\)", "", cleaned)

        # Remove the artist portion before " - ".
        # Example: Artist - Song Name
        if " - " in cleaned:
            parts = cleaned.split(" - ", 1)

            if artist and artist.lower() in parts[0].lower():
                cleaned = parts[1]
            else:
                cleaned = parts[1]

        # Handle pipe-separated titles.
        # Example: Song Name | Official Audio
        elif " | " in cleaned:
            cleaned = cleaned.split(" | ", 1)[0]

        # Remove common metadata words.
        noise_pattern = re.compile(
            r"\b("
            r"official\s+video|"
            r"official\s+audio|"
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

        cleaned = noise_pattern.sub("", cleaned)

        # Remove special characters.
        cleaned = re.sub(r"[^\w\s]", "", cleaned)

        # Remove extra spaces.
        cleaned = re.sub(r"\s+", " ", cleaned).strip()

        return cleaned.lower()

    # =========================================================
    # 2. CHECK FOR SAME SONG OR VARIANT
    # =========================================================

    def _is_same_or_variant(
        self,
        candidate_title: str,
        clean_seed_title: str,
    ) -> bool:
        """
        Check whether a candidate title is the same song
        or a likely variant of the original song.
        """

        candidate_clean = self._extract_clean_title(candidate_title)

        if not clean_seed_title or not candidate_clean:
            return False

        # Direct title containment.
        if (
            clean_seed_title in candidate_clean
            or candidate_clean in clean_seed_title
        ):
            return True

        # Compare meaningful words.
        seed_words = {
            word
            for word in clean_seed_title.split()
            if len(word) > 2
        }

        candidate_words = set(candidate_clean.split())

        if seed_words and seed_words.issubset(candidate_words):
            return True

        return False

    # =========================================================
    # 3. SEARCH YOUTUBE
    # =========================================================

    def search_tracks(
        self,
        query: str,
        max_results: int = 9,
    ) -> list[dict]:
        """
        Search YouTube for tracks.

        Returns a list of dictionaries containing:
        ID, title, uploader, duration, thumbnail, and URL.
        """

        options = {
            **self.base_opts,
            "extract_flat": True,
            "skip_download": True,
        }

        results = []

        try:
            with yt_dlp.YoutubeDL(options) as ydl:
                info = ydl.extract_info(
                    f"ytsearch{max_results}:{query}",
                    download=False,
                )

                for entry in info.get("entries", []):
                    if not entry:
                        continue

                    video_id = entry.get("id")

                    if not video_id:
                        continue

                    thumbnails = entry.get("thumbnails") or []

                    thumbnail = entry.get("thumbnail", "")

                    if not thumbnail and thumbnails:
                        thumbnail = thumbnails[-1].get("url", "")

                    results.append(
                        {
                            "id": video_id,
                            "title": entry.get(
                                "title",
                                "Unknown Track",
                            ),
                            "uploader": (
                                entry.get("uploader")
                                or entry.get("channel")
                                or "Unknown Artist"
                            ),
                            "duration": entry.get("duration") or 0,
                            "thumbnail": thumbnail,
                            "webpage_url": (
                                entry.get("webpage_url")
                                or entry.get("url")
                                or (
                                    "https://www.youtube.com/watch?v="
                                    f"{video_id}"
                                )
                            ),
                        }
                    )

        except Exception as error:
            print(f"[Search Error] {error}")

        return results

    # =========================================================
    # 4. RANDOM MUSIC DISCOVERY
    # =========================================================

    def get_trending_tracks(
        self,
        count: int = 9,
    ) -> list[dict]:
        """
        Select a random discovery query and search YouTube.

        A different query may be selected on each call.
        """

        random_seed = random.choice(self.discovery_queries)

        return self.search_tracks(
            random_seed,
            max_results=count,
        )

    # =========================================================
    # 5. GET SIMILAR TRACKS
    # =========================================================

    def get_similar_tracks(
        self,
        current_track: dict,
        count: int = 8,
    ) -> list[dict]:
        """
        Find tracks related to the currently playing song.

        First:
            Try YouTube's Mix/Radio playlist.

        Fallback:
            Search using the artist's name.

        The original song and obvious variants are excluded.
        """

        video_id = current_track.get("id")
        raw_title = current_track.get("title", "")
        artist = current_track.get("uploader", "")

        clean_seed_title = self._extract_clean_title(
            raw_title,
            artist,
        )

        results = []

        # -----------------------------------------------------
        # METHOD 1: YOUTUBE RADIO MIX
        # -----------------------------------------------------

        if video_id:
            mix_url = (
                f"https://www.youtube.com/watch?v={video_id}"
                f"&list=RD{video_id}"
            )

            options = {
                **self.base_opts,
                "extract_flat": True,
                "playlist_items": f"1-{count + 15}",
                "skip_download": True,
            }

            try:
                with yt_dlp.YoutubeDL(options) as ydl:
                    info = ydl.extract_info(
                        mix_url,
                        download=False,
                    )

                    for entry in info.get("entries", []):
                        if not entry:
                            continue

                        candidate_id = entry.get("id")
                        candidate_title = entry.get("title", "")

                        if not candidate_id:
                            continue

                        # Skip the original song.
                        if candidate_id == video_id:
                            continue

                        # Skip the same song or obvious variants.
                        if self._is_same_or_variant(
                            candidate_title,
                            clean_seed_title,
                        ):
                            continue

                        thumbnails = entry.get("thumbnails") or []

                        thumbnail = entry.get("thumbnail", "")

                        if not thumbnail and thumbnails:
                            thumbnail = thumbnails[-1].get("url", "")

                        if not thumbnail:
                            thumbnail = "assets/placeholder.png"

                        results.append(
                            {
                                "id": candidate_id,
                                "title": candidate_title,
                                "uploader": (
                                    entry.get("uploader")
                                    or entry.get("channel")
                                    or "Various Artists"
                                ),
                                "duration": entry.get("duration") or 0,
                                "thumbnail": thumbnail,
                                "webpage_url": (
                                    entry.get("webpage_url")
                                    or entry.get("url")
                                    or (
                                        "https://www.youtube.com/watch?v="
                                        f"{candidate_id}"
                                    )
                                ),
                            }
                        )

                        if len(results) >= count:
                            break

            except Exception as error:
                print(f"[Radio Mix Fetch Notice] {error}")

        # -----------------------------------------------------
        # METHOD 2: FALLBACK ARTIST SEARCH
        # -----------------------------------------------------

        if len(results) < count:
            fallback_query = (
                f"{artist} radio mix playlist top tracks"
            )

            candidates = self.search_tracks(
                fallback_query,
                max_results=25,
            )

            for candidate in candidates:
                candidate_id = candidate.get("id")
                candidate_title = candidate.get("title", "")

                # Skip the original video.
                if candidate_id == video_id:
                    continue

                # Skip the same song or its variants.
                if self._is_same_or_variant(
                    candidate_title,
                    clean_seed_title,
                ):
                    continue

                # Avoid duplicate video IDs.
                if any(
                    result.get("id") == candidate_id
                    for result in results
                ):
                    continue

                # Avoid duplicate or nearly identical titles.
                if any(
                    self._is_same_or_variant(
                        candidate_title,
                        self._extract_clean_title(
                            result.get("title", "")
                        ),
                    )
                    for result in results
                ):
                    continue

                results.append(candidate)

                if len(results) >= count:
                    break

        return results

    # =========================================================
    # 6. DOWNLOAD AND PREPARE AUDIO
    # =========================================================

    def prepare_audio_file(self, video_url: str, track_id: str) -> tuple[str | None, float]:
        target_path = os.path.abspath(os.path.join(self.cache_dir, f"{track_id}.m4a"))
        duration = 0.0

        opts = {
            **self.base_opts,
            'format': 'bestaudio[ext=m4a]/bestaudio/best',
            'outtmpl': os.path.join(self.cache_dir, f"{track_id}.%(ext)s"),
        }

        if not os.path.exists(target_path):
            try:
                with yt_dlp.YoutubeDL(opts) as ydl:
                    info = ydl.extract_info(video_url, download=True)
                    if info and info.get('duration'):
                        duration = float(info['duration'])
            except Exception as err:
                print(f"[Download Error] {err}")

        final_file = None
        for ext in ('m4a', 'mp3', 'ogg', 'opus', 'webm'):
            candidate = os.path.abspath(os.path.join(self.cache_dir, f"{track_id}.{ext}"))
            if os.path.exists(candidate):
                final_file = candidate
                break

        if not final_file:
            return None, 0.0

        if duration <= 0:
            try:
                mf = mutagen.File(final_file)
                if mf and mf.info and hasattr(mf.info, 'length'):
                    duration = float(mf.info.length)
            except Exception:
                pass

        return final_file, duration