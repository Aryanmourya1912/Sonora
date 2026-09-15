import os
import certifi
import yt_dlp

class DownloadManager:
    def __init__(self, download_dir: str):
        self.download_dir = download_dir
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