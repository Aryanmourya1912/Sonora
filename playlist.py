import os
import sqlite3
import json
from kivy.utils import platform


class PlaylistManager:
    def __init__(self, db_path: str = None):
        # 1. Anchor SQLite database to guaranteed writable app storage on Android
        if db_path:
            self.db_path = db_path
        elif platform == 'android':
            try:
                from kivymd.app import MDApp
                app = MDApp.get_running_app()
                base_dir = app.user_data_dir if app else os.path.expanduser("~")
                self.db_path = os.path.join(base_dir, "player_data.db")
            except Exception:
                self.db_path = "player_data.db"
        else:
            self.db_path = "player_data.db"

        # Ensure directory exists before connecting
        db_dir = os.path.dirname(os.path.abspath(self.db_path))
        if db_dir:
            os.makedirs(db_dir, exist_ok=True)

        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self._init_db()

    def _init_db(self):
        with self.conn:
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS playlists (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE NOT NULL,
                    tracks TEXT NOT NULL
                )
            """)
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS favorites (
                    id TEXT PRIMARY KEY,
                    track TEXT NOT NULL
                )
            """)
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS history (
                    id TEXT PRIMARY KEY,
                    track TEXT NOT NULL,
                    played_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS playback_state (
                    key TEXT PRIMARY KEY,
                    track TEXT NOT NULL,
                    position REAL NOT NULL
                )
            """)

    # ----------------- PERSISTENT PLAYBACK STATE -----------------
    def save_last_playback(self, track: dict, position: float):
        """Saves the last played song and stopped timestamp in seconds."""
        if not track:
            return
        clean_track = {
            'id': str(track.get('id', '')),
            'title': track.get('title', 'Unknown Track'),
            'uploader': track.get('uploader', 'Unknown Artist'),
            'duration': track.get('duration', 0),
            'thumbnail': track.get('thumbnail', ''),
            'webpage_url': track.get('webpage_url', ''),
            'local_path': track.get('local_path', '')
        }
        try:
            with self.conn:
                self.conn.execute("""
                    INSERT OR REPLACE INTO playback_state (key, track, position)
                    VALUES ('last_active', ?, ?)
                """, (json.dumps(clean_track), float(position or 0.0)))
        except Exception as e:
            print(f"[Playlist DB Save State Error] {e}")

    def get_last_playback(self) -> tuple[dict | None, float]:
        """Loads the last played song and stopped timestamp from the previous session."""
        try:
            cursor = self.conn.cursor()
            cursor.execute("SELECT track, position FROM playback_state WHERE key = 'last_active'")
            row = cursor.fetchone()
            if row:
                return json.loads(row[0]), float(row[1])
        except Exception as e:
            print(f"[Playlist DB Read State Error] {e}")
        return None, 0.0

    # ----------------- RECENT HISTORY (LAST 20 TRACKS) -----------------
    def add_to_history(self, track: dict):
        track_id = str(track.get('id', ''))
        if not track_id:
            return

        clean_track = {
            'id': track_id,
            'title': track.get('title', 'Unknown Track'),
            'uploader': track.get('uploader', 'Unknown Artist'),
            'duration': track.get('duration', 0),
            'thumbnail': track.get('thumbnail', ''),
            'webpage_url': track.get('webpage_url', ''),
            'local_path': track.get('local_path', '')
        }

        try:
            with self.conn:
                self.conn.execute("""
                    INSERT OR REPLACE INTO history (id, track, played_at)
                    VALUES (?, ?, CURRENT_TIMESTAMP)
                """, (track_id, json.dumps(clean_track)))

                self.conn.execute("""
                    DELETE FROM history WHERE id NOT IN (
                        SELECT id FROM history ORDER BY played_at DESC LIMIT 20
                    )
                """)
        except Exception as e:
            print(f"[Playlist DB Add History Error] {e}")

    def get_history(self) -> list[dict]:
        results = []
        try:
            cursor = self.conn.cursor()
            cursor.execute("SELECT track FROM history ORDER BY played_at DESC LIMIT 20")
            for row in cursor.fetchall():
                try:
                    results.append(json.loads(row[0]))
                except Exception:
                    continue
        except Exception as e:
            print(f"[Playlist DB Read History Error] {e}")
        return results

    # ----------------- FAVORITES / LIKED SONGS -----------------
    def is_favorite(self, track_id: str) -> bool:
        if not track_id:
            return False
        try:
            cursor = self.conn.cursor()
            cursor.execute("SELECT 1 FROM favorites WHERE id = ?", (str(track_id),))
            return cursor.fetchone() is not None
        except Exception:
            return False

    def toggle_favorite(self, track: dict) -> bool:
        track_id = str(track.get('id', ''))
        if not track_id:
            return False

        if self.is_favorite(track_id):
            try:
                with self.conn:
                    self.conn.execute("DELETE FROM favorites WHERE id = ?", (track_id,))
                return False
            except Exception as e:
                print(f"[Playlist DB Toggle Fav Error] {e}")
                return False
        else:
            clean_track = {
                'id': track_id,
                'title': track.get('title', 'Unknown Track'),
                'uploader': track.get('uploader', 'Unknown Artist'),
                'duration': track.get('duration', 0),
                'thumbnail': track.get('thumbnail', ''),
                'webpage_url': track.get('webpage_url', ''),
                'local_path': track.get('local_path', '')
            }
            try:
                with self.conn:
                    self.conn.execute(
                        "INSERT OR REPLACE INTO favorites (id, track) VALUES (?, ?)",
                        (track_id, json.dumps(clean_track))
                    )
                return True
            except Exception as e:
                print(f"[Playlist DB Toggle Fav Error] {e}")
                return False

    def get_favorites(self) -> list[dict]:
        results = []
        try:
            cursor = self.conn.cursor()
            cursor.execute("SELECT track FROM favorites ORDER BY rowid DESC")
            for row in cursor.fetchall():
                try:
                    results.append(json.loads(row[0]))
                except Exception:
                    continue
        except Exception as e:
            print(f"[Playlist DB Read Favs Error] {e}")
        return results

    # ----------------- PLAYLISTS -----------------
    def create_playlist(self, name: str) -> bool:
        name = name.strip()
        if not name:
            return False
        try:
            with self.conn:
                self.conn.execute("INSERT INTO playlists (name, tracks) VALUES (?, ?)", (name, json.dumps([])))
            return True
        except sqlite3.IntegrityError:
            return False
        except Exception as e:
            print(f"[Playlist DB Create Error] {e}")
            return False

    def delete_playlist(self, name: str):
        try:
            with self.conn:
                self.conn.execute("DELETE FROM playlists WHERE name = ?", (name,))
        except Exception as e:
            print(f"[Playlist DB Delete Error] {e}")

    def get_all_playlists(self) -> list[str]:
        try:
            cursor = self.conn.cursor()
            cursor.execute("SELECT name FROM playlists ORDER BY id DESC")
            return [row[0] for row in cursor.fetchall()]
        except Exception as e:
            print(f"[Playlist DB Get Playlists Error] {e}")
            return []

    def get_playlist_tracks(self, playlist_name: str) -> list[dict]:
        try:
            cursor = self.conn.cursor()
            cursor.execute("SELECT tracks FROM playlists WHERE name = ?", (playlist_name,))
            row = cursor.fetchone()
            return json.loads(row[0]) if row else []
        except Exception as e:
            print(f"[Playlist DB Read Tracks Error] {e}")
            return []

    def add_to_playlist(self, playlist_name: str, track: dict) -> bool:
        tracks = self.get_playlist_tracks(playlist_name)
        if any(t.get('id') == track.get('id') for t in tracks):
            return False

        clean_track = {
            'id': track.get('id', 'local_' + track.get('title', '')),
            'title': track.get('title', 'Unknown Track'),
            'uploader': track.get('uploader', 'Unknown Artist'),
            'duration': track.get('duration', 0),
            'thumbnail': track.get('thumbnail', ''),
            'webpage_url': track.get('webpage_url', ''),
            'local_path': track.get('local_path', '')
        }
        tracks.append(clean_track)
        try:
            with self.conn:
                self.conn.execute("UPDATE playlists SET tracks = ? WHERE name = ?", (json.dumps(tracks), playlist_name))
            return True
        except Exception as e:
            print(f"[Playlist DB Add Track Error] {e}")
            return False

    def remove_from_playlist(self, playlist_name: str, track_id: str):
        tracks = self.get_playlist_tracks(playlist_name)
        tracks = [t for t in tracks if t.get('id') != track_id]
        try:
            with self.conn:
                self.conn.execute("UPDATE playlists SET tracks = ? WHERE name = ?", (json.dumps(tracks), playlist_name))
        except Exception as e:
            print(f"[Playlist DB Remove Track Error] {e}")

    # ----------------- OFFLINE TRACKS -----------------
    def get_offline_tracks(self, download_dir: str = None) -> list[dict]:
        # Anchor downloads directory to writable user_data_dir on Android
        if download_dir:
            target_dir = download_dir
        elif platform == 'android':
            try:
                from kivymd.app import MDApp
                app = MDApp.get_running_app()
                base_dir = app.user_data_dir if app else os.path.expanduser("~")
                target_dir = os.path.join(base_dir, "downloads")
            except Exception:
                target_dir = "downloads"
        else:
            target_dir = "downloads"

        if not os.path.exists(target_dir):
            return []

        supported_exts = ('.mp3', '.m4a', '.opus', '.wav', '.ogg')
        offline_tracks = []
        try:
            for filename in sorted(os.listdir(target_dir)):
                if filename.lower().endswith(supported_exts):
                    full_path = os.path.abspath(os.path.join(target_dir, filename))
                    title = os.path.splitext(filename)[0]

                    track_duration = 0
                    try:
                        import mutagen
                        audio_info = mutagen.File(full_path)
                        if audio_info and audio_info.info and hasattr(audio_info.info, 'length'):
                            track_duration = int(audio_info.info.length)
                    except Exception:
                        pass

                    offline_tracks.append({
                        'id': f"local_{filename}",
                        'title': title,
                        'uploader': "Offline Storage",
                        'duration': track_duration,
                        'thumbnail': "assets/placeholder.png",
                        'webpage_url': '',
                        'local_path': full_path
                    })
        except Exception as dir_err:
            print(f"[Playlist DB Offline Scan Error] {dir_err}")

        return offline_tracks