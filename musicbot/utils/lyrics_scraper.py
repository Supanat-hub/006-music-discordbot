import re
import aiohttp
from bs4 import BeautifulSoup

# ---------- Title helpers ----------
def clean_title(raw_title: str) -> str:
    t = raw_title or ""
    t = re.sub(r"\s*[\(\[\{].*?[\)\]\}]\s*", " ", t)  # ลบวงเล็บและเนื้อใน
    t = re.sub(r"(?i)\b(official\s*video|official\s*audio|mv|m\/v|visualizer|lyrics?|thaisub|engsub)\b", "", t)
    t = re.sub(r"(?i)\b(feat\.?|ft\.?)\b.*", "", t)  # ตัดตั้งแต่ feat./ft.
    t = re.sub(r"\s{2,}", " ", t).strip(" -|–—·•\u00a0").strip()
    return t

def split_artist_title(title: str, fallback_artist: str = "Unknown"):
    c = clean_title(title)
    for sep in [" - ", " – ", " — ", " | ", " : "]:
        if sep in c:
            a, s = c.split(sep, 1)
            return a.strip(), s.strip()
    return fallback_artist, c

def _normalize_slug(s: str):
    s = re.sub(r"[^\w\s'-]", "", s, flags=re.UNICODE)
    s = s.replace("&", "and")
    s = re.sub(r"\s+", " ", s).strip()
    return s

# ---------- HTTP helpers ----------
async def _fetch_text(session: aiohttp.ClientSession, url: str) -> str | None:
    try:
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=10),
                               headers={"User-Agent": "Mozilla/5.0"}) as r:
            if r.status == 200:
                return await r.text()
    except Exception:
        return None
    return None

# ---------- Scrapers ----------
async def scrape_genius(session: aiohttp.ClientSession, artist: str, song: str) -> str | None:
    a = _normalize_slug(artist).lower().replace(" ", "-").replace("'", "")
    s = _normalize_slug(song).lower().replace(" ", "-").replace("'", "")
    url = f"https://genius.com/{a}-{s}-lyrics"
    html = await _fetch_text(session, url)
    if not html:
        return None
    soup = BeautifulSoup(html, "html.parser")
    blocks = soup.select('div[data-lyrics-container="true"]') or soup.select("div.Lyrics__Container-sc-1ynbvzw-6")
    if not blocks:
        return None
    parts = []
    for b in blocks:
        for br in b.find_all("br"):
            br.replace_with("\n")
        parts.append(b.get_text("\n", strip=False))
    lyrics = "\n".join(parts).strip()
    return lyrics or None

async def scrape_lyrics_fandom(session: aiohttp.ClientSession, artist: str, song: str) -> str | None:
    a = _normalize_slug(artist).title().replace(" ", "_")
    s = _normalize_slug(song).title().replace(" ", "_")
    url = f"https://lyrics.fandom.com/wiki/{a}:{s}"
    html = await _fetch_text(session, url)
    if not html:
        return None
    soup = BeautifulSoup(html, "html.parser")
    box = soup.select_one("div.lyricbox")
    if not box:
        return None
    for br in box.find_all("br"):
        br.replace_with("\n")
    text = box.get_text("\n", strip=False).strip()
    return re.sub(r"\n{3,}", "\n\n", text) or None

async def scrape_youtube_description(session: aiohttp.ClientSession, video_url: str) -> str | None:
    if not video_url or ("youtube.com" not in video_url and "youtu.be" not in video_url):
        return None
    html = await _fetch_text(session, video_url)
    if not html:
        return None
    m = re.search(r'(?is)(?:lyrics|เนื้อเพลง)\s*[:\-]\s*(.{50,2000})</', html)
    if not m:
        return None
    cand = BeautifulSoup(m.group(1), "html.parser").get_text("\n")
    cand = re.sub(r"\n{3,}", "\n\n", cand).strip()
    return cand if len(cand) > 50 else None

def chunk_text(txt: str, limit: int = 1900):
    chunks, cur, cur_len = [], [], 0
    for line in (txt or "").splitlines():
        add = line.rstrip() + "\n"
        if cur_len + len(add) > limit:
            chunks.append("".join(cur))
            cur, cur_len = [add], len(add)
        else:
            cur.append(add)
            cur_len += len(add)
    if cur:
        chunks.append("".join(cur))
    return chunks

# ---------- Facade ----------
async def get_lyrics(artist: str, song: str, video_url: str | None = None) -> str | None:
    async with aiohttp.ClientSession() as session:
        for scraper in (scrape_genius, scrape_lyrics_fandom):
            text = await scraper(session, artist, song)
            if text:
                return text
        if video_url:
            return await scrape_youtube_description(session, video_url)
    return None
