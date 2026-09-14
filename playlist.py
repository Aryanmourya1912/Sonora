import os
import sqlite3
import json

class PlaylistManager:
    def __init__(self, db_path: str = "player_data.db"):
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
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
        with self.conn:
            self.conn.execute("""
                INSERT OR REPLACE INTO playback_state (key, track, position)
                VALUES ('last_active', ?, ?)
            """, (json.dumps(clean_track), float(position or 0.0)))

    def get_last_playback(self) -> tuple[dict | None, float]:
        """Loads the last played song and stopped timestamp from the previous session."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT track, position FROM playback_state WHERE key = 'last_active'")
        row = cursor.fetchone()
        if row:
            try:
                return json.loads(row[0]), float(row[1])
            except Exception:
                pass
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

    def get_history(self) -> list[dict]:
        cursor = self.conn.cursor()
        cursor.execute("SELECT track FROM history ORDER BY played_at DESC LIMIT 20")
        return [json.loads(row[0]) for row in cursor.fetchall()]

    # ----------------- FAVORITES / LIKED SONGS -----------------
    def is_favorite(self, track_id: str) -> bool:
        if not track_id:
            return False
        cursor = self.conn.cursor()
        cursor.execute("SELECT 1 FROM favorites WHERE id = ?", (str(track_id),))
        return cursor.fetchone() is not None

    def toggle_favorite(self, track: dict) -> bool:
        track_id = str(track.get('id', ''))
        if not track_id:
            return False

        if self.is_favorite(track_id):
            with self.conn:
                self.conn.execute("DELETE FROM favorites WHERE id = ?", (track_id,))
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
            with self.conn:
                self.conn.execute(
                    "INSERT OR REPLACE INTO favorites (id, track) VALUES (?, ?)",
                    (track_id, json.dumps(clean_track))
                )
            return True

    def get_favorites(self) -> list[dict]:
        cursor = self.conn.cursor()
        cursor.execute("SELECT track FROM favorites ORDER BY rowid DESC")
        return [json.loads(row[0]) for row in cursor.fetchall()]

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

    def delete_playlist(self, name: str):
        with self.conn:
            self.conn.execute("DELETE FROM playlists WHERE name = ?", (name,))

    def get_all_playlists(self) -> list[str]:
        cursor = self.conn.cursor()
        cursor.execute("SELECT name FROM playlists ORDER BY id DESC")
        return [row[0] for row in cursor.fetchall()]

    def get_playlist_tracks(self, playlist_name: str) -> list[dict]:
        cursor = self.conn.cursor()
        cursor.execute("SELECT tracks FROM playlists WHERE name = ?", (playlist_name,))
        row = cursor.fetchone()
        return json.loads(row[0]) if row else []

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
        with self.conn:
            self.conn.execute("UPDATE playlists SET tracks = ? WHERE name = ?", (json.dumps(tracks), playlist_name))
        return True

    def remove_from_playlist(self, playlist_name: str, track_id: str):
        tracks = self.get_playlist_tracks(playlist_name)
        tracks = [t for t in tracks if t.get('id') != track_id]
        with self.conn:
            self.conn.execute("UPDATE playlists SET tracks = ? WHERE name = ?", (json.dumps(tracks), playlist_name))

    # ----------------- OFFLINE TRACKS -----------------
    def get_offline_tracks(self, download_dir: str = "downloads") -> list[dict]:
        if not os.path.exists(download_dir):
            return []

        supported_exts = ('.mp3', '.m4a', '.opus', '.wav', '.ogg')
        offline_tracks = []
        for filename in sorted(os.listdir(download_dir)):
            if filename.lower().endswith(supported_exts):
                full_path = os.path.abspath(os.path.join(download_dir, filename))
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
        return offline_tracks