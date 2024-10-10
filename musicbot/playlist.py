import yt_dlp as ytdl
import discord

YTDL_OPTS = {
    "default_search": "ytsearch",
    "format": "bestaudio/best",
    "quiet": True,
    "noplaylist": False,
    "extract_flat": "in_playlist",
    "no_warnings": True,
    "cookiefile": "cookies.txt",
    "postprocessors": [{
        "key": "FFmpegExtractAudio",
        "preferredcodec": "m4a",
        "preferredquality": "192",
    }],
}

musicrun_logo = "https://i.ibb.co/6s134j9/musicrun.gif"

class Videoplaylist:
    """Class containing information about a particular video."""
    ydl = ytdl.YoutubeDL(YTDL_OPTS)  # Reuse YoutubeDL instance

    def __init__(self, url_or_search, requested_by, num_song):
        """Plays audio from (or searches for) a URL."""
        self.numsong = num_song
        video = self._get_info(url_or_search)
        self.stream_url = video["url"]
        playlist = self.ydl.extract_info(url_or_search, download=False)
        self.title_playlist = playlist["title"]
        self.video_url_playlist = playlist["webpage_url"]
        self.video_url = video["webpage_url"]
        self.title = video["title"]
        self.uploader = video.get("uploader", "")
        self.thumbnail = video.get("thumbnail")
        self.requested_by = requested_by

    def _get_info(self, video_url):
        info = self.ydl.extract_info(video_url, download=False)
        if info.get("_type") == "playlist":
            return self._get_info(info["entries"][self.numsong]["url"])  # get info for first video
        else:
            return info

    def get_embed(self):
        """Makes an embed out of this Video's information."""
        embed = discord.Embed(
            title=f"Playlist -> {self.title_playlist}", description=self.uploader, url=self.video_url_playlist, color=0xF3F4F9)
        embed.set_author(name="006 music", icon_url=musicrun_logo)
        embed.set_footer(
            text=f"Requested by {self.requested_by.name}",
            icon_url=self.requested_by.avatar)
        embed.set_thumbnail(url="https://i.ibb.co/LPHd5Bp/yt-playlist-img.jpg")
        return embed
