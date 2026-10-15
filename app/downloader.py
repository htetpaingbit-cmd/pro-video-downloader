import os
import re
import yt_dlp
from app.utils import clean_filename

DOWNLOAD_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "downloads"))
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

DESKTOP_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
    'Accept-Language': 'en-US,en;q=0.9',
}

class DownloaderEngine:
    @staticmethod
    def get_info(url: str) -> dict:
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'skip_download': True,
            'extract_flat': False,
            'http_headers': DESKTOP_HEADERS,
            'age_limit': 99,
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)

            if 'entries' in info:
                entries = list(info.get('entries', []))
                if entries:
                    info = entries[0]
                else:
                    raise Exception("ဗီဒီယို မတွေ့ရှိပါ")

            duration_secs = info.get('duration', 0)
            mins, secs = divmod(duration_secs, 60)
            duration_str = f"{int(mins):02d}:{int(secs):02d}" if duration_secs else "Short Video"

            filesize = info.get('filesize') or info.get('filesize_approx')
            
            def calc_mb(size_bytes, fallback_bitrate_kbps=1500):
                if size_bytes:
                    return f"{round(size_bytes / (1024 * 1024), 1)} MB"
                elif duration_secs:
                    calc_bytes = (duration_secs * fallback_bitrate_kbps * 1024) / 8
                    return f"~{round(calc_bytes / (1024 * 1024), 1)} MB"
                return "Unknown"

            sizes = {
                "1080": calc_mb(filesize, fallback_bitrate_kbps=3000),
                "720": calc_mb(filesize, fallback_bitrate_kbps=1500),
                "480": calc_mb(filesize, fallback_bitrate_kbps=800),
                "mp3": calc_mb(None, fallback_bitrate_kbps=192)
            }

            return {
                "title": info.get('title', 'Video'),
                "thumbnail": info.get('thumbnail', ''),
                "duration": duration_str,
                "uploader": info.get('uploader', 'Creator'),
                "sizes": sizes,
                "original_url": info.get('webpage_url', url)
            }

    @staticmethod
    def process_download(url: str, quality: str, progress_hook=None) -> tuple[str, str]:
        if quality == "mp3":
            format_str = 'ba/b'
        elif quality == "1080":
            format_str = 'b[height<=1080]/bv*[height<=1080]+ba/b'
        elif quality == "720":
            format_str = 'b[height<=720]/bv*[height<=720]+ba/b'
        elif quality == "480":
            format_str = 'b[height<=480]/bv*[height<=480]+ba/b'
        else:
            format_str = 'b/best'

        out_template = os.path.join(DOWNLOAD_DIR, "%(id)s.%(ext)s")
        
        ydl_opts = {
            'format': format_str,
            'outtmpl': out_template,
            'quiet': True,
            'no_warnings': True,
            'writethumbnail': False,
            'windowsfilenames': True,
            'http_headers': DESKTOP_HEADERS,
            'age_limit': 99,
        }

        if progress_hook:
            ydl_opts['progress_hooks'] = [progress_hook]

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            meta = ydl.extract_info(url, download=True)
            saved_filename = ydl.prepare_filename(meta)
            safe_title = clean_filename(meta.get('title', 'downloaded_video'))
            return saved_filename, safe_title