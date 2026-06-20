import asyncio
import yt_dlp as ytdl
import discord
from functools import partial

# Options for extracting audio stream URL
# extract_flat: discard_in_playlist = flatten search/playlist entries (gives page URLs)
# but fully extract single video URLs (gives stream URL + full metadata)
YTDL_OPTS = {
    "no_check_certificate": True,
    "restrictfilenames": True,
    "outtmpl": "%(extractor)s-%(id)s-%(title)s.%(ext)s",
    # "cookiefile": "cookies.txt",
    "default_search": "ytsearch",
    "format": "bestaudio[ext=webm]/bestaudio[ext=m4a]/bestaudio/best",
    "extract_flat": "discard_in_playlist",
    "quiet": True,
    "noplaylist": True,
    "no_warnings": True,
    "source_address": "0.0.0.0",
    "socket_timeout": 15,
    "retries": 5,
    "postprocessors": [],
}

# Options for browsing playlists only (extract_flat enabled — does NOT fetch audio format)
YTDL_PLAYLIST_OPTS = {
    "no_check_certificate": True,
    "quiet": True,
    "noplaylist": False,
    "extract_flat": True,
    "no_warnings": True,
    "source_address": "0.0.0.0",
    "socket_timeout": 15,
}

musicrun_logo = "https://i.ibb.co/6s134j9/musicrun.gif"

ydl = ytdl.YoutubeDL(YTDL_OPTS)
ydl_playlist = ytdl.YoutubeDL(YTDL_PLAYLIST_OPTS)

class Video:
    """คลาสสำหรับจัดการข้อมูลวิดีโอ"""

    def __init__(self, data, requested_by):
        """รับข้อมูลดิบมาเก็บไว้เลย ไม่ต้องโหลดใหม่"""
        self.stream_url = data.get("url")
        self.video_url = data.get("webpage_url")
        self.title = data.get("title")
        self.uploader = data.get("uploader", "Unknown")
        self.thumbnail = data.get("thumbnail")
        self.duration = data.get("duration") # เก็บความยาวเพลงไว้ด้วยก็ได้
        self.requested_by = requested_by

    @classmethod
    async def create(cls, url_or_search, requested_by, loop=None):
        """Factory Method สำหรับสร้าง Video object แบบไม่บล็อกบอท"""
        loop = loop or asyncio.get_running_loop()

        to_run = partial(ydl.extract_info, url=url_or_search, download=False)
        data = await loop.run_in_executor(None, to_run)

        # จัดการกรณีเป็น Playlist หรือ Search Result (เอาตัวแรก)
        if data.get("_type") == "playlist":
            if "entries" in data and len(data["entries"]) > 0:
                first_entry = data["entries"][0]
                # ใช้ webpage_url ก่อน (YouTube page URL) เพราะถ้าใช้ url อาจได้ stream URL (videoplayback)
                # ซึ่งจะทำให้ดึง metadata ไม่ได้
                first_url = (
                    first_entry.get("webpage_url")
                    or first_entry.get("original_url")
                    or (f"https://www.youtube.com/watch?v={first_entry['id']}" if first_entry.get("id") else None)
                    or first_entry.get("url")
                )
                if not first_url:
                    raise Exception("Could not determine video URL from search results.")
                to_run_sub = partial(ydl.extract_info, url=first_url, download=False)
                data = await loop.run_in_executor(None, to_run_sub)
            else:
                raise Exception("Playlist is empty or could not be loaded.")

        return cls(data, requested_by)
    
    async def refresh_stream_url(self, loop=None):
        """
        ฟังก์ชันสำหรับดึงลิงก์เสียงใหม่สดๆ ก่อนเล่น (Lazy Loading)
        ช่วยแก้ปัญหาลิงก์หมดอายุเมื่อคิวยาวๆ
        """
        loop = loop or asyncio.get_running_loop()
        
        # ใช้ video_url (ที่เป็นลิงก์ YouTube ถาวร) ไปขอลิงก์เสียงใหม่
        to_run = partial(ydl.extract_info, url=self.video_url, download=False)
        data = await loop.run_in_executor(None, to_run)
        
        # อัปเดต stream_url ใน object นี้ให้เป็นของใหม่
        self.stream_url = data.get("url")
        # กันเหนียว: อัปเดต title ด้วยเผื่อมีการเปลี่ยน
        self.title = data.get("title") 
        
        return self

    def get_embed(self):
        """สร้าง Embed สำหรับเพลง"""
        embed = discord.Embed(
            title=self.title, description=self.uploader, url=self.video_url, color=0xF3F4F9
        )
        embed.set_author(name="006 music", icon_url=musicrun_logo)
        embed.set_footer(
            text=f"Requested by {self.requested_by.name}",
            icon_url=self.requested_by.avatar.url if self.requested_by.avatar else None
        )
        if self.thumbnail:
            embed.set_thumbnail(url=self.thumbnail)
        return embed
