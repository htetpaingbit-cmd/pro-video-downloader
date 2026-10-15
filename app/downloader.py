import os
import re
import requests
import yt_dlp
from app.utils import clean_filename

DOWNLOAD_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "downloads"))
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

DESKTOP_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
    'Accept-Language': 'en-US,en;q=0.9',
}

COBALT_SERVERS = [
    "https://api.cobalt.tools",
    "https://co.wuk.sh",
    "https://cobalt.api.scav.top"
]

def extract_youtube_id(url: str) -> str:
    match = re.search(r'(?:youtu\.be\/|youtube\.com\/(?:embed\/|v\/|watch\?v=|watch\?.+&v=))([\w-]{11})', url)
    return match.group(1) if match else None

class DownloaderEngine:
    @staticmethod
    def get_info(url: str) -> dict:
        yt_id = extract_youtube_id(url)

        # ⭐️ YouTube အတွက် Google တရားဝင် OEmbed API (ဘယ်တော့မှ Bot Block မမိပါ) ⭐️
        if yt_id:
            try:
                clean_yt_url = f"https://www.youtube.com/watch?v=yt_id"
                oembed_url = f"https://www.youtube.com/oembed?url=https://www.youtube.com/watch?v={yt_id}&format=json"
                r = requests.get(oembed_url, timeout=5)
                if r.status_code == 200:
                    data = r.json()
                    return {
                        "title": data.get("title", "YouTube Video"),
                        "thumbnail": f"https://i.ytimg.com/vi/{yt_id}/hqdefault.jpg",
                        "duration": "YouTube Video",
                        "uploader": data.get("author_name", "YouTube Creator"),
                        "sizes": {
                            "1080": "~35.0 MB",
                            "720": "~18.0 MB",
                            "480": "~9.0 MB",
                            "mp3": "~4.5 MB"
                        },
                        "original_url": url
                    }
            except Exception:
                pass

        # ⭐️ TikTok, Facebook, Adult Sites များအတွက် မူလအတိုင်း yt-dlp သုံးခြင်း (Perfect ဖြစ်ပြီးသား) ⭐️
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
        yt_id = extract_youtube_id(url)

        # ⭐️ YouTube ဒေါင်းလုဒ်ဆွဲခြင်း (Cobalt Global Engine) ⭐️
        if yt_id:
            payload = {
                "url": f"https://www.youtube.com/watch?v={yt_id}",
                "videoQuality": "720" if quality in ["720", "1080"] else "480",
                "downloadMode": "audio" if quality == "mp3" else "auto"
            }
            headers = {"Accept": "application/json", "Content-Type": "application/json"}

            for server in COBALT_SERVERS:
                try:
                    res = requests.post(f"{server}/", json=payload, headers=headers, timeout=12)
                    if res.status_code == 200:
                        data = res.json()
                        stream_url = data.get("url")
                        if stream_url:
                            ext = "mp3" if quality == "mp3" else "mp4"
                            out_path = os.path.join(DOWNLOAD_DIR, f"{yt_id}.{ext}")
                            
                            r = requests.get(stream_url, stream=True, timeout=40)
                            with open(out_path, "wb") as f:
                                for chunk in r.iter_content(chunk_size=1024 * 1024):
                                    if chunk:
                                        f.write(chunk)
                            return out_path, f"youtube_{yt_id}"
                except Exception:
                    continue

        # ⭐️ TikTok, Facebook, Adult Sites အတွက် မူလအတိုင်း yt-dlp သုံးခြင်း ⭐️
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
