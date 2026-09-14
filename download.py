import os
import threading
import yt_dlp

class SafeLogger:
    """Silences yt-dlp output to prevent crashing on redirected streams."""
    def debug(self, msg): pass
    def info(self, msg): pass
    def warning(self, msg): pass
    def error(self, msg):
        print(f"[Download Error] {msg}")

class Downloader:
    def __init__(self, download_dir: str = "downloads"):
        self.download_dir = download_dir
        os.makedirs(self.download_dir, exist_ok=True)

    def download_track(self, video_url: str, on_complete=None, on_error=None):
        def _task():
            opts = {
                'format': 'bestaudio/best',
                'outtmpl': os.path.join(self.download_dir, '%(title)s.%(ext)s'),
                'writethumbnail': True,
                'postprocessors': [
                    # 1. Convert to MP3
                    {
                        'key': 'FFmpegExtractAudio',
                        'preferredcodec': 'mp3',
                        'preferredquality': '192',
                    },
                    # 2. Write track Title, Artist, and Year into ID3 tags
                    {
                        'key': 'FFmpegMetadata',
                        'add_metadata': True,
                    },
                    # 3. Embed the downloaded thumbnail as album artwork
                    {
                        'key': 'EmbedThumbnail',
                        'already_have_thumbnail': False,
                    },
                ],
                'quiet': True,
                'no_warnings': True,
                'logger': SafeLogger(),
                'nocheckcertificate': True,
            }
            try:
                with yt_dlp.YoutubeDL(opts) as ydl:
                    ydl.download([video_url])
                if on_complete:
                    on_complete()
            except Exception as e:
                print(f"[Downloader Error] {e}")
                if on_error:
                    on_error(str(e))

        threading.Thread(target=_task, daemon=True).start()