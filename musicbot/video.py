import yt_dlp as ytdl
import discord

YTDL_OPTS = {
    "cookiefile": "cookies.txt",
    "default_search": "ytsearch",
    "format": "bestaudio/best",
    "quiet": True,
    "noplaylist": False,
    "extract_flat": "in_playlist",
    "no_warnings": True,
    "postprocessors": [{
        "key": "FFmpegExtractAudio",
        "preferredcodec": "m4a",
        "preferredquality": "192",
    }],
}
musicrun_logo = "https://i.ibb.co/6s134j9/musicrun.gif"

class Video:
    """Class containing information about a particular video."""

    ydl = ytdl.YoutubeDL(YTDL_OPTS)  # Reuse YoutubeDL instance

    def _get_info(self, video_url):
        info = self.ydl.extract_info(video_url, download=False)
        if info.get("_type") == "playlist":
            return self._get_info(info["entries"][0]["url"])  # get info for first video
        else:
            return info
        
    def __init__(self, url_or_search, requested_by):
        """Plays audio from (or searches for) a URL."""
        video = self._get_info(url_or_search)
        self.stream_url = video["url"]
        self.video_url = video["webpage_url"]
        self.title = video["title"]
        self.uploader = video.get("uploader", "")
        self.thumbnail = video.get("thumbnail")
        self.requested_by = requested_by

    

    def get_embed(self):
        """Makes an embed out of this Video's information."""
        embed = discord.Embed(
            title=self.title, description=self.uploader, url=self.video_url, color=0xF3F4F9)
        embed.set_author(name="006 music", icon_url=musicrun_logo)
        embed.set_footer(
            text=f"Requested by {self.requested_by.name}",
            icon_url=self.requested_by.avatar)
        if self.thumbnail:
            embed.set_thumbnail(url=self.thumbnail)
        return embed
