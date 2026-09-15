import os
import certifi
import yt_dlp
from kivy.utils import platform

class DownloadManager:
    def __init__(self, download_dir: str = None):
        # Auto-detect safe writable storage if no folder is passed
        if download_dir:
            self.download_dir = download_dir
        elif platform == 'android':
            try:
                from jnius import autoclass
                PythonActivity = autoclass('org.kivy.android.PythonActivity')
                context = PythonActivity.mActivity
                base = context.getExternalFilesDir(None).getAbsolutePath()
                self.download_dir = os.path.join(base, "downloads")
            except Exception:
                self.download_dir = os.path.abspath("downloads")
        else:
            self.download_dir = os.path.abspath("downloads")

        os.makedirs(self.download_dir, exist_ok=True)

    def download_track(self, video_url: str, title: str) -> bool:
        if not video_url:
            return False

        safe_title = "".join(c for c in title if c.isalnum() or c in (' ', '_', '-')).strip()
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

# Alias so both 'Downloader' and 'DownloadManager' work seamlessly
Downloader = DownloadManager