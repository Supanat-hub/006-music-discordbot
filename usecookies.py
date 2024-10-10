import yt_dlp as ytdl

YTDL_OPTS = {
    "default_search": "ytsearch",
    "format": "bestaudio/best",
    "quiet": True,
    "cookiefile": "cookies.txt",  # ชื่อไฟล์คุกกี้
}

ydl = ytdl.YoutubeDL(YTDL_OPTS)

url = "https://youtu.be/TtfjkcuomT8?si=m_9WRtzIiym2aXCG"
info = ydl.extract_info(url, download=False)
print(info)
