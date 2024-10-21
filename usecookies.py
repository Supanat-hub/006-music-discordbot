import yt_dlp as ytdl
YTDL_OPTS = {
    "default_search": "ytsearch",
    "format": "bestaudio/best",
    "cookiefile": "cookies.txt",
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
# YTDL_OPTS = {
#     "default_search": "ytsearch",
#     "format": "bestaudio/best",
#     "quiet": True,
#     "cookiefile": "cookies.txt",  # ชื่อไฟล์คุกกี้
# }
class Video:
    url = "https://www.youtube.com/watch?v=XpHXRb51nqg"
    ydl = ytdl.YoutubeDL(YTDL_OPTS)

    def _get_info(self, url):
            info = self.ydl.extract_info(url, download=False)
            if info.get("_type") == "playlist":
                return self._get_info(info["entries"][0]["url"])  # get info for first video
            else:
                return info

print(Video._get_info(Video, "https://www.youtube.com/watch?v=XpHXRb51nqg"))


