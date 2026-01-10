import asyncio
import yt_dlp as ytdl
import discord
from functools import partial

YTDL_OPTS = {
    "no_check_certificate": True,
    "restrictfilenames": True,
    "outtmpl": "%(extractor)s-%(id)s-%(title)s.%(ext)s",
    # "cookiefile": "cookies.txt",
    "default_search": "auto",
    "format": "bestaudio/best",
    "quiet": True,
    "noplaylist": True,
    "extract_flat": "in_playlist",
    "no_warnings": True,
    "source_address": "0.0.0.0",
    "socket_timeout": 10,
    "retries": 3,
}
musicrun_logo = "https://i.ibb.co/6s134j9/musicrun.gif"

ydl = ytdl.YoutubeDL(YTDL_OPTS)

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

        # จัดการกรณีเป็น Playlist (เอาตัวแรก)
        if data.get("_type") == "playlist":
            if "entries" in data and len(data["entries"]) > 0:
                # ถ้าเป็น playlist ต้องดึงข้อมูลตัวแรกอีกรอบ เพราะ extract_flat ให้ข้อมูลมาไม่ครบ
                first_url = data["entries"][0]["url"]
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
