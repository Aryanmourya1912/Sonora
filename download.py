import os
import certifi
import yt_dlp
from kivy.utils import platform


class DownloadManager:
    def __init__(self, download_dir: str = None):
        # Anchor downloads to user_data_dir so playlist.py and download.py match
        if download_dir:
            self.download_dir = download_dir
        elif platform == 'android':
            try:
                from kivymd.app import MDApp
                app = MDApp.get_running_app()
                base_dir = app.user_data_dir if app else os.path.expanduser("~")
                self.download_dir = os.path.join(base_dir, "downloads")
            except Exception:
                self.download_dir = os.path.abspath("downloads")
        else:
            self.download_dir = os.path.abspath("downloads")

        try:
            os.makedirs(self.download_dir, exist_ok=True)
        except Exception as e:
            print(f"[Download Dir Error] {e}")

    def download_track(self, video_url: str, title: str = "track") -> bool:
        if not video_url:
            return False

        # Guard against None or non-string title
        raw_title = str(title or "track").strip()
        safe_title = "".join(c for c in raw_title if c.isalnum() or c in (' ', '_', '-')).strip()

        # Fallback if title was made entirely of special characters/emojis
        if not safe_title:
            import time
            safe_title = f"track_{int(time.time())}"

        out_path = os.path.join(self.download_dir, f"{safe_title}.%(ext)s")

        ydl_opts = {
            'format': 'bestaudio[ext=m4a]/bestaudio/best',
            'outtmpl': out_path,
            'nocheckcertificate': True,
            'quiet': True,
            'no_warnings': True,
            'cachedir': False,
            'noplaylist': True,
            'prefer_ffmpeg': False,
        }

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([video_url])
            return True
        except Exception as e:
            print(f"[Download Error] {e}")
            return False


# Alias so both imports work seamlessly
Downloader = DownloadManager