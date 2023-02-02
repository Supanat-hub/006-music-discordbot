import youtube_dl as ytdl
import discord

YTDL_OPTS = {
    "default_search": "ytsearch",
    "format": "bestaudio/best",
    "quiet": True,
    "noplaylis": False,
    "extract_flat": "in_playlist"
}
musicrun_logo = "https://i.ibb.co/6s134j9/musicrun.gif"

class Videoplaylist:
    """Class containing information about a particular video."""

    def __init__(self, url_or_search, requested_by, num_song):
        """Plays audio from (or searches for) a URL."""
        with ytdl.YoutubeDL(YTDL_OPTS) as ydl:
            self.numsong = num_song
            video = self._get_info(url_or_search)
            playlist = ydl.extract_info(url_or_search, download=False)
            self.title_playlist = playlist["title"]
            self.title = video["title"]
            self.video_url_playlist = playlist["webpage_url"]
            video_format = video["formats"][0]
            self.stream_url = video_format["url"]
            self.uploader = playlist["uploader"] if "uploader" in video else ""
            self.requested_by = requested_by

    def _get_info(self, video_url):
        with ytdl.YoutubeDL(YTDL_OPTS) as ydl:
            info = ydl.extract_info(video_url, download=False)
            video = None
            if "_type" in info and info["_type"] == "playlist":
                return self._get_info(
                    info["entries"][self.numsong]["url"])  # get info for first video
            else:
                video = info
            return video

    

    def get_embed(self):
        """Makes an embed out of this Video's information."""
        embed = discord.Embed(
            title=f"added {self.title_playlist} to playlist queue", description=self.uploader, url=self.video_url_playlist, color=0xF3F4F9)
        embed.set_author(name="006 music", icon_url=musicrun_logo)
        embed.set_footer(
            text=f"Requested by {self.requested_by.name}",
            icon_url=self.requested_by.avatar)
        embed.set_thumbnail(url="https://drive.google.com/uc?export=view&id=1IyWjfzZ4XC3Ny8JAmdHaq8TonpnWqqd7")
        return embed
