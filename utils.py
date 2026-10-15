import re
import requests
from urllib.parse import urlparse, urlunparse

def sanitize_url(raw_url: str) -> str:
    # Link အဆုံးတွင် ကပ်ပါလာတတ်သော ' " space စသည့် အမှိုက်များကို အလိုအလျောက် ရှင်းထုတ်ခြင်း
    raw_url = raw_url.strip().strip("'\"`<> ")
    
    if "vt.tiktok.com" in raw_url:
        try:
            resp = requests.head(raw_url, allow_redirects=True, timeout=5, headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            })
            raw_url = resp.url
        except Exception:
            pass

    parsed = urlparse(raw_url)
    if "tiktok.com" in parsed.netloc:
        return urlunparse((parsed.scheme, parsed.netloc, parsed.path, '', '', ''))
        
    if "youtube.com" in parsed.netloc and "/watch" in parsed.path:
        query_match = re.search(r'v=[a-zA-Z0-9_-]+', parsed.query)
        clean_query = query_match.group(0) if query_match else ""
        return urlunparse((parsed.scheme, parsed.netloc, parsed.path, '', clean_query, ''))
        
    if "youtu.be" in parsed.netloc:
        return urlunparse((parsed.scheme, parsed.netloc, parsed.path, '', '', ''))
        
    return raw_url

def clean_filename(title: str) -> str:
    cleaned = re.sub(r'[\\/*?:"<>|\r\n\t]', "", title)
    cleaned = re.sub(r'\s+', " ", cleaned).strip()
    return cleaned[:60] if cleaned else "video"