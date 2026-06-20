import asyncio
from datetime import datetime
from functools import partial
import math
from pytz import timezone
import logging
import discord
from discord import app_commands
from discord.ext import commands
from ..video import Video
import yt_dlp as youtube_dl
import urllib
from ..utils.lyrics_scraper import get_lyrics, split_artist_title, chunk_text


#url
alert_url = "https://i.ibb.co/ykzmssp/aleart.gif"
logo_bot = "https://i.ibb.co/6PmVgYx/logo-bot.png"

YTDL_OPTS = {
    "no_check_certificate": True,
    "restrictfilenames": True,
    "outtmpl": "%(extractor)s-%(id)s-%(title)s.%(ext)s",
    "cookiefile": "cookies.txt",
    "default_search": "ytsearch",
    "format": "bestaudio[ext=webm]/bestaudio[ext=m4a]/bestaudio/best",
    "extract_flat": "discard_in_playlist",
    "quiet": True,
    "noplaylist": True,
    "no_warnings": True,
    "source_address": "0.0.0.0",
    "socket_timeout": 15,
    "retries": 5,
}

FFMPEG_BEFORE_OPTS = '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5 -probesize 10M'
"""
Command line options to pass to `ffmpeg` before the `-i`.

See https://stackoverflow.com/questions/43218292/youtubedl-read-error-with-discord-py/44490434#44490434 for more information.
Also, https://ffmpeg.org/ffmpeg-protocols.html for command line option reference.
"""

async def audio_playing(ctx):
    """Checks that audio is currently playing before continuing."""
    client = ctx.guild.voice_client
    if client and client.channel and client.source:
        return True
    else:
        raise commands.CommandError("Not currently playing any audio.")


async def in_voice_channel(ctx):
    """Checks that the command sender is in the same voice channel as the bot."""
    voice = ctx.author.voice
    bot_voice = ctx.guild.voice_client
    if voice and bot_voice and voice.channel and bot_voice.channel and voice.channel == bot_voice.channel:
        return True
    else:
        raise commands.CommandError(
            "You need to be in the channel to do that.")


async def is_audio_requester(ctx):
    """Checks that the command sender is the song requester."""
    music = ctx.bot.get_cog("Music")
    state = music.get_state(ctx.guild)
    permissions = ctx.channel.permissions_for(ctx.author)
    if permissions.administrator or state.is_requester(ctx.author):
        return True
    else:
        raise commands.CommandError(
            "You need to be the song requester to do that.")

def timetz(*args):
    return datetime.now(tz).timetuple()
tz = timezone('Asia/Bangkok') #time zone list https://gist.github.com/heyalexej/8bf688fd67d7199be4a1682b3eec7568
logging.Formatter.converter = timetz

def make_progress_bar(current, total, tag='Downloading', bar_length=10):
    filled_length = int(bar_length * current // total)
    bar = '🟦' * filled_length + '⬜' * (bar_length - filled_length)
    percent = int(100 * current / total)
    return f"**{tag}**\n{bar} `{current}/{total} ({percent}%)`"

class Music(commands.Cog):
    def __init__(self, bot: commands.Bot, config) -> None:
        self.bot = bot
        self.config = config[__name__.split(".")[-1]]  # retrieve module name, find config entry
        self.states = {}
    
    def get_state(self, guild):
        """Gets the state for `guild`, creating it if it does not exist."""
        if guild in self.states:
            return self.states[guild]
        else:
            self.states[guild] = GuildState()
            return self.states[guild]

    async def _play_next(self, ctx, state):
        """ฟังก์ชันสำหรับเตรียมเพลงถัดไป (Lazy Load) แล้วส่งไปเล่น"""
        if len(state.playlist) > 0:
            song = state.playlist.pop(0)
            
            try:
                logging.info(f"🔄 Refreshing link for: {song.title}")
                await song.refresh_stream_url(self.bot.loop)
                self._play_song(ctx.guild.voice_client, state, song)
                
            except Exception as e:
                logging.error(f"Error refreshing song {song.title}: {e}")
                # if state.text_channel:
                #     try:
                #         # await state.text_channel.send(f"⚠️ เล่นเพลง {song.title} ไม่ได้ (Link Error) กำลังข้าม...", delete_after=10)
                #         pass
                #     except Exception:
                #         pass
                await self._play_next(ctx, state)
        else:
            state.now_playing = None
            await ctx.guild.voice_client.disconnect()
            logging.info("Queue finished so disconnected.")

    def _play_song(self, client, state, song):
        state.now_playing = song
        # สร้าง Source
        source = discord.PCMVolumeTransformer(
            discord.FFmpegPCMAudio(
                song.stream_url, 
                before_options=FFMPEG_BEFORE_OPTS,
                options='-vn'
            ),
            volume=state.volume
        )

        def after_playing(err):
            if err:
                logging.error(f"Player error: {err}")
            
            # กรณี Loop เพลงเดิม
            if state.repeat:
                # ถ้า Loop ก็ต้องเรียกผ่าน Task เหมือนกัน (เผื่อลิงก์หมดอายุระหว่าง Loop)
                coro = song.refresh_stream_url(self.bot.loop)
                future = asyncio.run_coroutine_threadsafe(coro, self.bot.loop)
                try:
                    future.result() # รอให้ Refresh เสร็จ
                    self._play_song(client, state, song)
                except Exception:
                    # ถ้า Refresh ไม่ผ่านตอน Loop ให้ข้าม
                    asyncio.run_coroutine_threadsafe(self._play_next(client, state), self.bot.loop)
                return

            # กรณีเล่นเพลงถัดไป
            asyncio.run_coroutine_threadsafe(
                self._play_next(client, state), 
                self.bot.loop
            )

        client.play(source, after=after_playing)
        logging.info(f"▶️ Now playing: {song.title}")

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        state = self.get_state(member.guild.id)
        voice_state = member.guild.voice_client
        if member == self.bot.user:  #CATCH
            return
        if after.channel is None: #User has left a voice channel
            if voice_state is None:
                # Exiting if the bot it's not connected to a voice channel
                return 
            if len(voice_state.channel.members) == 1:
                logging.info(f"Loop Off | In : {member.guild.name} Id :{member.guild.id}")
                state.playlist = []
                state.repeat = False
                state.now_playing = None
                await voice_state.disconnect()
                logging.info(f"Disconnected no one in VC. | In : {member.guild.name} Id :{member.guild.id}")
        if before.channel is not after.channel: # Change voice channel.
            if voice_state is None:
                # Exiting if the bot it's not connected to a voice channel
                return
            await asyncio.sleep(5)
            if len(voice_state.channel.members) == 1:
                logging.info(f"Loop Off | In : {member.guild.name} Id :{member.guild.id}")
                state.playlist = []
                state.repeat = False
                state.now_playing = None
                await voice_state.disconnect()
                logging.info(f"Disconnected no one in VC. | In : {member.guild.name} Id :{member.guild.id}")        
        else:
            return
    

    @app_commands.guild_only()
    @app_commands.command(
        name="reset_bot",
        description="reset stagement."
    )
    async def _resetbot(self, interaction: discord.Interaction):
        if interaction.permissions.administrator :
            try:
                client = interaction.guild.voice_client
                await client.disconnect()
                await client.cleanup()
            except:
                pass
            state = self.get_state(interaction.guild_id)
            state.volume = 1.0
            state.playlist = []
            state.now_playing = None
            state.repeat = False
            await interaction.response.send_message(content="**Done!**", embed=None, ephemeral=True)
        else:
            await interaction.response.send_message(content="**You must to be an adminstrator.!**", embed=None, ephemeral=True)
    @app_commands.command(
        name = "donate",
        description = "Donate server charge."
    )
    async def _donate(self, interaction: discord.Interaction) -> None:
        emBed = discord.Embed(title="**Donate**",url="https://tmn.app.link/R1hfCx6fmub", description="ช่องทางการสนับสนุน", color=0xF3F4F9)
        emBed.add_field(name='1.True money', value='By this QR-CODE')
        emBed.set_image(url="https://i.ibb.co/DRbp7PD/QR-code-true.jpg")
        emBed.set_author(name="006 music",  icon_url="https://i.ibb.co/bzYLcyp/money-fly.gif")
        emBed.add_field(name='2.True money(Link)', value='Click the blue-title on top')
        await interaction.response.send_message(embed=emBed)
    @app_commands.command(
        name="avatar",
        description="get user avater."
    )
    async def _avatar(self, interaction: discord.Interaction, member: discord.Member):
        embed = discord.Embed(title="Avatar", description=f"- {member.mention}")
        embed.set_image(url=member.avatar.url)
        await interaction.response.send_message(embed=embed)
    
    @app_commands.guild_only()
    @app_commands.command(
        name="play",
        description="play song by url/name"
    )
    async def _play(self, interaction: discord.Interaction, search: str):
        """Plays audio hosted at <url> (or performs a search for <url> and plays the first result)."""
        await interaction.response.defer()
        state = self.get_state(interaction.guild_id)  # get the guild's state
        state.text_channel = interaction.channel
        channel = discord.VoiceChannel = None
        if not channel:
            try:
                channel = interaction.user.voice.channel
            except AttributeError:
                emBed5 = discord.Embed(color=0xff0000)
                emBed5.add_field(name='เกิดข้อผิดพลาด T_T', value='กรุณาเชื่อมต่อช่องเสียงก่อน')
                await interaction.followup.send(content=None, embed=emBed5)
                await asyncio.sleep(10)
                await interaction.delete_original_response()
                return
        client = interaction.guild.voice_client
        if client and client.channel:
            voice_run = discord.utils.get(self.bot.voice_clients, guild=interaction.guild)
            if voice_run.channel != interaction.user.voice.channel:
                emBed5 = discord.Embed(color=0xff0000)
                emBed5.add_field(name='เกิดข้อผิดพลาด T_T', value='คุณไม่ได้อยู่ช่องเดียวกับบอทจึงไม่สามารถใช้คำสั่งนี้ได้\n- ขณะนี้บอทกำลังอยู่ในช่อง **{0}**'.format(voice_run.channel))
                emBed5.set_author(name="006 music", icon_url=alert_url)
                await interaction.followup.send(content=None, embed=emBed5)
                await asyncio.sleep(10)
                await interaction.delete_original_response()
                return 
            if state.repeat == True:
                emBed5 = discord.Embed(color=0xff0000)
                emBed5.add_field(name='เกิดข้อผิดพลาด T_T', value="Can't add any song when loop is **on**")
                emBed5.set_author(name="006 music", icon_url=alert_url)
                await interaction.followup.send(content=None, embed=emBed5)
                await asyncio.sleep(10)
                await interaction.delete_original_response()
                return 
            try:
                video = await Video.create(search, interaction.user, self.bot.loop)
            except youtube_dl.DownloadError as e:
                logging.warn(f"Error downloading song: {e} | In : {interaction.guild.name} Id :{interaction.guild_id}")
                await interaction.followup.send(content="There was an error downloading your song, **sorry.**", embed=None)
                return
            state.playlist.append(video)
            if not client.is_playing():
                await self._play_next(interaction, state)
            await interaction.followup.send(content=None, embed=video.get_embed())
        else:
            if interaction.user.voice is not None and interaction.user.voice.channel is not None:
                channel = interaction.user.voice.channel
                try:
                    video = await Video.create(search, interaction.user, self.bot.loop)
                except youtube_dl.DownloadError as e:
                    await interaction.followup.send(content="There was an error downloading your song, **sorry.**", embed=None)
                    return
                client = await channel.connect()
                await interaction.guild.change_voice_state(channel=channel, self_mute=False, self_deaf=True)
                self._play_song(client, state, video)
                await interaction.followup.send(content=None, embed=video.get_embed())
            else:
                raise commands.CommandError(
                    "You need to be in a voice channel to do that.")
            
    @app_commands.guild_only()
    @app_commands.command(name="lyrics", description="ดึงเนื้อเพลงจากชื่อเพลงที่ระบุ")
    async def lyrics(self, interaction: discord.Interaction, song: str):
        """ผู้ใช้พิมพ์ชื่อเพลงเข้ามา เช่น 'Ariana Grande - pov'"""
        await interaction.response.defer(thinking=True)
        # พยายามแยก artist–title จากข้อความที่ผู้ใช้กรอก
        artist, title = split_artist_title(song, fallback_artist="Unknown")
        text = await get_lyrics(artist, title)
        if not text:
            await interaction.followup.send(f"หาเนื้อเพลงไม่เจอสำหรับ **{artist} – {title}** 😢")
            return

        for i, part in enumerate(chunk_text(text, limit=3900), start=1):
            embed = discord.Embed(
                title=f"เนื้อเพลง: {artist} – {title}" + (f" (ส่วน {i})" if i > 1 else ""),
                description=part, color=0xF3F4F9
            )
            await interaction.followup.send(embed=embed)
    
    @app_commands.guild_only()
    @app_commands.command(
        name="play-playlist",
        description="play playlist by url only."
    )
    async def _playplaylist(self, interaction: discord.Interaction, url: str):
        """Plays audio hosted at <url> (or performs a search for <url> and plays the first result)."""
        await interaction.response.send_message("**wait for it....**")
        client = interaction.guild.voice_client
        state = self.get_state(interaction.guild_id)  # get the guild's state
        state.text_channel = interaction.channel
        channel = None
        voice_run = discord.utils.get(self.bot.voice_clients, guild=interaction.guild)
        
        # Check if URL contains playlist
        if "youtube.com/playlist" not in url:
            emBed5 = discord.Embed(color=0xff0000)
            emBed5.add_field(name='เกิดข้อผิดพลาด T_T', value='This is not a playlist url.')
            emBed5.set_author(name="006 music", icon_url=alert_url)
            await interaction.edit_original_response(content=None, embed=emBed5)
            await asyncio.sleep(10)
            await interaction.delete_original_response()
            return

        if not channel:
            try:
                channel = interaction.user.voice.channel
            except AttributeError:
                emBed5 = discord.Embed(color=0xff0000)
                emBed5.add_field(name='เกิดข้อผิดพลาด T_T', value='กรุณาเชื่อมต่อช่องเสียงก่อน')
                await interaction.edit_original_response(content=None, embed=emBed5)
                await asyncio.sleep(10)
                await interaction.delete_original_response()
                return

        if client and client.channel:
            if voice_run.channel != interaction.user.voice.channel:
                emBed5 = discord.Embed(color=0xff0000)
                emBed5.add_field(name='เกิดข้อผิดพลาด T_T', value='คุณไม่ได้อยู่ช่องเดียวกับบอทจึงไม่สามารถใช้คำสั่งนี้ได้\n- ขณะนี้บอทกำลังอยู่ในช่อง **{0}**'.format(voice_run.channel))
                emBed5.set_author(name="006 music", icon_url=alert_url)
                await interaction.edit_original_response(content=None, embed=emBed5)
                await asyncio.sleep(10)
                await interaction.delete_original_response()
                return  
            if state.repeat == True:
                emBed5 = discord.Embed(color=0xff0000)
                emBed5.add_field(name='เกิดข้อผิดพลาด T_T', value="Can't add any song when loop is **on**")
                emBed5.set_author(name="006 music", icon_url=alert_url)
                await interaction.edit_original_response(content=None, embed=emBed5)
                await asyncio.sleep(10)
                await interaction.delete_original_response()
                return  
            
            try:
                loop = self.bot.loop or asyncio.get_running_loop()
                to_run = partial(youtube_dl.YoutubeDL(YTDL_OPTS).extract_info, url, download=False)
                info = await loop.run_in_executor(None, to_run)
                entries = info.get("entries", [])
                d = len(entries)
                if d == 0:
                    await interaction.edit_original_response(content="Playlist is empty.", embed=None)
                    return
                if d > 50:
                    emBed5 = discord.Embed(color=0xff0000)
                    emBed5.add_field(name='เกิดข้อผิดพลาด T_T', value='ไม่สามารถเล่นได้ เนื่องจากมีวิดีโอในเพลลิสต์มากกว่า 50 ')
                    emBed5.set_author(name="006 music", icon_url=alert_url)
                    await interaction.edit_original_response(content=None, embed=emBed5)
                    await asyncio.sleep(10)
                    await interaction.delete_original_response()
                    return
                
                if "_type" in info and info["_type"] == "playlist":
                    await interaction.edit_original_response(content="**processing...**")
                    itac = interaction.user
                    success = 0
                    fail = 0
                    for i, entry in enumerate(entries):
                        video_url = entry.get('webpage_url') or entry.get('url')
                        if not video_url:
                            continue
                        try:
                            video = Video({"webpage_url": video_url, "title": entry.get("title") or "Unknown"}, itac)
                            state.playlist.append(video)
                            success += 1
                        except Exception as e:
                            logging.error(f"Error adding song from playlist: {e}")
                            fail += 1
                            continue
                        if (i+1) % 2 == 0 or (i+1) == d:
                            bar = make_progress_bar(i+1, d)
                            await interaction.edit_original_response(content=f"{bar} เพิ่มเพลงสำเร็จ {success} | ล้มเหลว {fail}")
                    
                    if not client.is_playing():
                        await self._play_next(interaction, state)
            except Exception as e:
                logging.error(f"Error downloading playlist: {e}")
                await interaction.edit_original_response(content="There was an error downloading your playlist, **sorry.**", embed=None)
                return
            
            if state.finish == True:
                await interaction.edit_original_response(content=f"**เพิ่มเพลงสำเร็จ {success} | ล้มเหลว {fail}**", embed=state.playlist[0].get_embed() if len(state.playlist) > 0 else None)
            else:
                emBed5 = discord.Embed(color=0xff0000)
                emBed5.add_field(name='เกิดข้อผิดพลาด T_T', value='Fail to add playlist, Try again later.')
                emBed5.set_author(name="006 music", icon_url=alert_url)
                await interaction.edit_original_response(content=None, embed=emBed5)
                state.playlist = []
                state.repeat = False
                state.now_playing = None
                state.finish = True
        else:
            if interaction.user.voice is not None and interaction.user.voice.channel is not None:
                channel = interaction.user.voice.channel
                try:
                    loop = self.bot.loop or asyncio.get_running_loop()
                    to_run = partial(youtube_dl.YoutubeDL(YTDL_OPTS).extract_info, url, download=False)
                    info = await loop.run_in_executor(None, to_run)
                except Exception as e:
                    logging.error(f"Error extracting playlist: {e}")
                    await interaction.edit_original_response(content="There was an error downloading your playlist, **sorry.**", embed=None)
                    return
                
                entries = info.get("entries", [])
                d = len(entries)
                if d == 0:
                    await interaction.edit_original_response(content="Playlist is empty.", embed=None)
                    return
                if d > 50:
                    emBed5 = discord.Embed(color=0xff0000)
                    emBed5.add_field(name='เกิดข้อผิดพลาด T_T', value='ไม่สามารถเล่นได้ เนื่องจากมีวิดีโอในเพลลิสต์มากกว่า 50 ')
                    emBed5.set_author(name="006 music", icon_url=alert_url)
                    await interaction.edit_original_response(content=None, embed=emBed5)
                    await asyncio.sleep(10)
                    await interaction.delete_original_response()
                    return
                
                try:
                    first_url = entries[0].get('webpage_url') or entries[0].get('url')
                    video = await Video.create(first_url, interaction.user, self.bot.loop)
                except Exception as e:
                    logging.error(f"Error creating first video: {e}")
                    await interaction.edit_original_response(content="There was an error playing the first video of the playlist.", embed=None)
                    return

                client = await channel.connect()
                await interaction.guild.change_voice_state(channel=channel, self_mute=False, self_deaf=True)
                self._play_song(client, state, video)
                
                await interaction.edit_original_response(content="**processing...**")
                itac = interaction.user
                success = 1
                fail = 0
                for i, entry in enumerate(entries[1:], start=1):
                    video_url = entry.get('webpage_url') or entry.get('url')
                    if not video_url:
                        continue
                    try:
                        video_obj = Video({"webpage_url": video_url, "title": entry.get("title") or "Unknown"}, itac)
                        state.playlist.append(video_obj)
                        success += 1
                    except Exception as e:
                        logging.warn(f"Error adding song: {e}")
                        fail += 1
                        continue
                    if (i+1) % 2 == 0 or (i+1) == d:
                        bar = make_progress_bar(i+1, d)
                        await interaction.edit_original_response(content=f"{bar} เพิ่มเพลงสำเร็จ {success} | ล้มเหลว {fail}")
                
                if state.finish == True:
                    await interaction.edit_original_response(content=f"**เพิ่มเพลงสำเร็จ {success} | ล้มเหลว {fail}**", embed=state.now_playing.get_embed() if state.now_playing else video.get_embed())
                else:
                    emBed5 = discord.Embed(color=0xff0000)
                    emBed5.add_field(name='เกิดข้อผิดพลาด T_T', value='Fail to add playlist, Try again later.')
                    emBed5.set_author(name="006 music", icon_url=alert_url)
                    await interaction.edit_original_response(content=None, embed=emBed5)
                    state.playlist = []
                    state.repeat = False
                    state.now_playing = None
                    state.finish = True
                
            else:
                raise commands.CommandError(
                    "You need to be in a voice channel to do that.")

    @app_commands.guild_only()
    @app_commands.command(
        name="loop",
        description="loop only one song."
    )
    async def _loop(self, interaction: discord.Interaction):
        channel = discord.VoiceChannel = None
        if not channel:
            try:
                channel = interaction.user.voice.channel
            except AttributeError:
                emBed5 = discord.Embed(color=0xff0000)
                emBed5.add_field(name='เกิดข้อผิดพลาด T_T', value='กรุณาเชื่อมต่อช่องเสียงก่อน')
                await interaction.response.send_message(content = None, embed=emBed5)
                await asyncio.sleep(10)
                await interaction.delete_original_response()
                return
        voice_run = discord.utils.get(self.bot.voice_clients, guild=interaction.guild)
        client = interaction.guild.voice_client
        if client and client.channel:
            if voice_run.channel != interaction.user.voice.channel:
                emBed5 = discord.Embed(color=0xff0000)
                emBed5.add_field(name='เกิดข้อผิดพลาด T_T', value='คุณไม่ได้อยู่ช่องเดียวกับบอทจึงไม่สามารถใช้คำสั่งนี้ได้\n- ขณะนี้บอทกำลังอยู่ในช่อง **{0}**'.format(voice_run.channel))
                emBed5.set_author(name="006 music", icon_url=alert_url)
                await interaction.response.send_message(content=None, embed=emBed5)
                await asyncio.sleep(10)
                await interaction.delete_original_response()
                return 
        if client and client.channel and client.source:
            state = self.get_state(interaction.guild_id)
            mode = state.repeat
            if mode == False:
                state.repeat = True
                await interaction.response.send_message(content="loop **On**", embed=None)
                logging.info(f"Loop On | In : {interaction.guild.name} Id :{interaction.guild_id}")
            elif mode == True:
                state.repeat = False
                await interaction.response.send_message(content="loop **Off**", embed=None)
                logging.info(f"Loop Off | In : {interaction.guild.name} Id :{interaction.guild_id}")
            return
        else:
            raise commands.CommandError("Not currently playing any audio.")

    @app_commands.guild_only()
    @app_commands.command(
        name="nowplaying",
        description="show currently playing song."
    )
    async def _nowplaying(self, interaction: discord.Interaction):
        state = self.get_state(interaction.guild.id)
        voice_run = discord.utils.get(self.bot.voice_clients, guild=interaction.guild)
        if voice_run == None:
            emBed4 = discord.Embed(color=0xff0000)
            emBed4.add_field(name='เกิดข้อผิดพลาด T_T', value='บอทไม่ได้เชื่อมต่อกับช่องเสียงอยู่')
            emBed4.set_author(name="006 music", icon_url=alert_url)
            await interaction.response.send_message(embed=emBed4, delete_after=5)
            return
        if not voice_run.is_playing():
            emBed5 = discord.Embed(color=0xff0000)
            emBed5.add_field(name='เกิดข้อผิดพลาด T_T', value='เพลงไม่ได้เล่นอยู่')
            emBed5.set_author(name="006 music", icon_url=alert_url)
            await interaction.response.send_message(embed=emBed5, delete_after=10)
            return
        if state.repeat == True:
            await interaction.response.send_message(content="**Now loop this**", embed=state.now_playing.get_embed())
            return
        else:
            await interaction.response.send_message(content="**Now playing**", embed=state.now_playing.get_embed())

    @app_commands.guild_only()
    @app_commands.command(
        name="delete",
        description="delete song in queue."
    )
    async def _detete(self, interaction: discord.Interaction, number: int):
        client = interaction.guild.voice_client
        if client and client.channel and client.source:
            state = self.get_state(interaction.guild_id)
            num = (number - 1)
            if num < 0:
                await interaction.response.send_message(content="**No such song in queue**")
                return
            try:
                queue = state.playlist
                delete = f"**{queue[num].title}**"
                state.playlist.pop(num)
                await interaction.response.send_message(content=f"**Deleted** : {delete}")
            except ValueError:
                await interaction.response.send_message(content=f"**Don't have song No.{number} in queue**")
                logging.info(f"{ValueError} | In : {interaction.guild.name} Id :{interaction.guild_id}")
                return
        else:
            await interaction.response.send_message(content="**Not currently playing any audio.**")
        
    @app_commands.guild_only()
    @app_commands.command(
        name="queue",
        description="show songs queue."
    )
    async def _queue(self, interaction: discord.Interaction):
        client = interaction.guild.voice_client
        if client and client.channel and client.source:
            state = self.get_state(interaction.guild_id)
            if state.repeat == True:
                message = await interaction.response.send_message(content="**now loop this**", embed=state.now_playing.get_embed())
                return 
            queue = state.playlist
            # await ctx.send(embed=self._queue_text(state.playlist))
            if len(queue) > 0:
                fmt = "\n".join(f"- {index+1}. **{song.title}**"for (index, song) in enumerate(queue))
                # add individual songs
                embed2 = discord.Embed(title=f'รายการเพลงที่ยังไม่ได้เล่น - ทั้งหมด {len(queue)}', description=fmt, color=0xC1E1C1)
                await interaction.response.send_message(embed=embed2)
            else:
                await interaction.response.send_message(content="The play queue is empty.")
        else:
            await interaction.response.send_message(content="**Not currently playing any audio.**")
    @app_commands.guild_only()
    @app_commands.command(
        name="skip",
        description="skip song."
    )
    async def _skip(self, interaction: discord.Interaction):
        """Skips the currently playing song, or votes to skip it."""
        state = self.get_state(interaction.guild_id)
        voice_run = discord.utils.get(self.bot.voice_clients, guild=interaction.guild)
        if voice_run == None:
            emBed4 = discord.Embed(color=0xff0000)
            emBed4.add_field(name='เกิดข้อผิดพลาด T_T', value='บอทไม่ได้เชื่อมต่อกับช่องเสียงอยู่')
            emBed4.set_author(name="006 music", icon_url=alert_url)
            await interaction.response.send_message(embed=emBed4, delete_after=5)
            return
        try:
            if voice_run.channel != interaction.user.voice.channel:
                emBed5 = discord.Embed(color=0xff0000)
                emBed5.add_field(name='เกิดข้อผิดพลาด T_T', value='คุณไม่ได้อยู่ช่องเดียวกับบอทจึงไม่สามารถใช้คำสั่งนี้ได้\nขณะนี้บอทกำลังอยู่ในช่อง{0}'.format(voice_run.channel))
                emBed5.set_author(name="006 music", icon_url=alert_url)
                await interaction.response.send_message(embed=emBed5, delete_after=10)
                return
            elif not voice_run.is_playing():
                emBed5 = discord.Embed(color=0xff0000)
                emBed5.add_field(name='เกิดข้อผิดพลาด T_T', value='เพลงไม่ได้เล่นอยู่จึง ข้ามไม่ได้')
                emBed5.set_author(name="006 music", icon_url=alert_url)
                await interaction.response.send_message(embed=emBed5, delete_after=10)
                return
            elif state.repeat == True:
                emBed5 = discord.Embed(color=0xff0000)
                emBed5.add_field(name='เกิดข้อผิดพลาด T_T', value="Can't skip song when loop is **on**")
                emBed5.set_author(name="006 music", icon_url=alert_url)
                await interaction.response.send_message(content=None, embed=emBed5, delete_after=10)
                await asyncio.sleep(10)
                await interaction.delete_original_response()
                return 
        except:
            await interaction.response.send_message(content="You need to be in the channel to do that.")
            return
                
        
        emBed6 = discord.Embed(color=0xF3F4F9)
        emBed6.add_field(name='ข้ามเพลงแล้ว', value=(f'**`{interaction.user.name}`**: Skipped the song!'))
        await interaction.response.send_message(embed=emBed6)
        voice_run.stop()

    @app_commands.guild_only()
    @app_commands.command(
        name="pause",
        description="pause or resume song."
    )
    async def _pause(self, interaction: discord.Interaction):
        state = self.get_state(interaction.guild_id)
        voice_run = discord.utils.get(self.bot.voice_clients, guild=interaction.guild)
        if voice_run == None:
            emBed4 = discord.Embed(color=0xff0000)
            emBed4.add_field(name='เกิดข้อผิดพลาด T_T', value='บอทไม่ได้เชื่อมต่อกับช่องเสียงอยู่')
            emBed4.set_author(name="006 music", icon_url=alert_url)
            await interaction.response.send_message(embed=emBed4)
            return

        if voice_run.channel != interaction.user.voice.channel:
            emBed5 = discord.Embed(color=0xff0000)
            emBed5.add_field(name='เกิดข้อผิดพลาด T_T', value='คุณไม่ได้อยู่ช่องเดียวกับบอทจึงไม่สามารถใช้คำสั่งนี้ได้\n- ขณะนี้บอทกำลังอยู่ในช่อง **{0}**'.format(voice_run.channel))
            emBed5.set_author(name="006 music", icon_url=alert_url)
            await interaction.response.send_message(embed=emBed5)
            return
        voice = interaction.user.voice
        bot_voice = interaction.guild.voice_client
        if voice and bot_voice and voice.channel and bot_voice.channel and voice.channel == bot_voice.channel:
            """Pauses any currently playing audio."""
            client = interaction.guild.voice_client
            self._pause_audio_slash(client)
            await interaction.response.send_message(content="**Done.**")
        else:
            raise commands.CommandError(
                "You need to be in the channel to do that.")
    def _pause_audio_slash(self, client):
        if client.is_paused():
            client.resume()
        else:
            client.pause()

    @app_commands.guild_only()
    @app_commands.command(
        name="clear_queue",
        description="clear all queues"
    )
    async def _clearqueue(self, interaction: discord.Interaction):
        client = interaction.guild.voice_client
        if client and client.channel and client.source:
            """Clears the play queue without leaving the channel."""
            state = self.get_state(interaction.guild_id)
            state.playlist = []
            await interaction.response.send_message(content="**Done.**")
        else:
            await interaction.response.send_message(content="**Not currently playing any audio.**")

    @app_commands.guild_only()
    @app_commands.command(
        name="volume",
        description="change volume"
    )
    async def _volume(self, interaction: discord.Interaction, volume: int):
        """Change the volume of currently playing audio (values 0-250)."""
        state = self.get_state(interaction.guild_id)
        voice_run = discord.utils.get(self.bot.voice_clients, guild=interaction.guild)
        if voice_run == None:
            emBed4 = discord.Embed(color=0xff0000)
            emBed4.add_field(name='เกิดข้อผิดพลาด T_T', value='บอทไม่ได้เชื่อมต่อกับช่องเสียงอยู่')
            emBed4.set_author(name="006 music", icon_url=alert_url)
            await interaction.response.send_message(embed=emBed4)
            return

        if voice_run.channel != interaction.user.voice.channel:
            emBed5 = discord.Embed(color=0xff0000)
            emBed5.add_field(name='เกิดข้อผิดพลาด T_T', value='คุณไม่ได้อยู่ช่องเดียวกับบอทจึงไม่สามารถใช้คำสั่งนี้ได้\n- ขณะนี้บอทกำลังอยู่ในช่อง **{0}**'.format(voice_run.channel))
            emBed5.set_author(name="006 music", icon_url=alert_url)
            await interaction.response.send_message(embed=emBed5)
            return
        voice = interaction.user.voice
        bot_voice = interaction.guild.voice_client
        if voice and bot_voice and voice.channel and bot_voice.channel and voice.channel == bot_voice.channel:
            # make sure volume is nonnegative
            if volume < 0:
                volume = 0
            max_vol = self.config["max_volume"]
            if max_vol > -1:  # check if max volume is set
                # clamp volume to [0, max_vol]
                if volume > max_vol:
                    volume = max_vol

            client = interaction.guild.voice_client

            state.volume = float(volume) / 100.0
            await interaction.response.send_message(content=f"volume `{volume}`", embed=None)
            client.source.volume = state.volume  # update the AudioSource's volume to match
            
        else:
            raise commands.CommandError(
                "You need to be in the channel to do that.")
    @app_commands.guild_only()
    @app_commands.command(
        name="leave",
        description="leave channel and clear queue"
    )
    async def _leave(self, interaction: discord.Interaction):
        """Leaves the voice channel, if currently in one."""
        voice_client = discord.utils.get(self.bot.voice_clients, guild=interaction.guild)
        if voice_client == None or not voice_client.is_connected():
            emBed6 = discord.Embed(color=0xff0000)
            emBed6.add_field(name='เกิดข้อผิดพลาด T_T', value='บอทไม่ได้อยู่ในช่องเพลงใดๆ')
            emBed6.set_author(name="006 music", icon_url=alert_url)
            await interaction.response.send_message(embed=emBed6, delete_after=5)
            return
        if voice_client.channel != interaction.user.voice.channel:
            emBed5 = discord.Embed(color=0xff0000)
            emBed5.add_field(name='เกิดข้อผิดพลาด T_T', value='คุณไม่ได้อยู่ช่องเดียวกับบอทจึงไม่สามารถใช้คำสั่งนี้ได้\n- ขณะนี้บอทกำลังอยู่ในช่อง **{0}**'.format(voice_client.channel))
            emBed5.set_author(name="006 music", icon_url=alert_url)
            await interaction.response.send_message(embed=emBed5, delete_after=10)
            return
        client = interaction.guild.voice_client
        state = self.get_state(interaction.guild_id)
        emBed3 = discord.Embed(color=0xF3F4F9)
        emBed3.add_field(name='006 music ได้ออกจากช่องแล้ว', value='disconnected')
        await interaction.response.send_message(embed=emBed3)
        await client.disconnect()
        client.cleanup()
        logging.info(f"Loop Off | In : {interaction.guild.name} Id :{interaction.guild_id}")
        state.playlist = []
        state.repeat = False
        state.now_playing = None
    
    @app_commands.command(
        name="ping",
        description="ping of bot"
    )
    async def _ping(self, interaction: discord.Interaction):
        emBed = discord.Embed(color=0xF3F4F9)
        emBed.add_field(name='__**Pong! 🏓**__', value=f"👉 ping: {round(self.bot.latency * 1000)} ms 👈")
        await interaction.response.send_message(embed=emBed)

    @commands.command()
    @commands.guild_only()
    async def ping(self, ctx):
        emBed = discord.Embed(color=0xF3F4F9)
        emBed.add_field(name='__**Pong! 🏓**__', value=f"👉 ping: {round(self.bot.latency * 1000)} ms 👈")
        await ctx.send(embed=emBed)

    @commands.command(aliases=["stop", "l", "L"])
    @commands.guild_only()
    # @commands.has_permissions(administrator=True)
    async def leave(self, ctx):
        """Leaves the voice channel, if currently in one."""
        voice_client = discord.utils.get(self.bot.voice_clients, guild=ctx.guild)
        if voice_client == None or not voice_client.is_connected():
            emBed6 = discord.Embed(color=0xff0000)
            emBed6.add_field(name='เกิดข้อผิดพลาด T_T', value='บอทไม่ได้อยู่ในช่องเพลงใดๆ')
            emBed6.set_author(name="006 music", icon_url=alert_url)
            await ctx.send(embed=emBed6, delete_after=5)
            await asyncio.sleep(5)
            await ctx.message.delete()
            return
        if voice_client.channel != ctx.author.voice.channel:
            emBed5 = discord.Embed(color=0xff0000)
            emBed5.add_field(name='เกิดข้อผิดพลาด T_T', value='คุณไม่ได้อยู่ช่องเดียวกับบอทจึงไม่สามารถใช้คำสั่งนี้ได้\n- ขณะนี้บอทกำลังอยู่ในช่อง **{0}**'.format(voice_client.channel))
            emBed5.set_author(name="006 music", icon_url=alert_url)
            await ctx.send(embed=emBed5, delete_after=10)
            await asyncio.sleep(10)
            await ctx.message.delete()
            return 
        client = ctx.guild.voice_client
        state = self.get_state(ctx.guild.id)
        emBed3 = discord.Embed(color=0xff0000)
        emBed3.add_field(name='006 music ได้ออกจากช่องแล้ว', value='disconnected')
        await ctx.send(embed=emBed3)
        await client.disconnect()
        logging.info(f"Loop Off | In : {ctx.guild.name} Id :{ctx.guild.id}")
        state.playlist = []
        state.repeat = False
        state.now_playing = None

    @commands.command(aliases=["resume"])
    @commands.guild_only()
    @commands.check(audio_playing)
    @commands.check(in_voice_channel)
    # @commands.check(is_audio_requester)
    async def pause(self, ctx):
        """Pauses any currently playing audio."""
        client = ctx.guild.voice_client

        self._pause_audio(client)
        await ctx.send("✅ฺ")

    def _pause_audio(self, client):
        if client.is_paused():
            client.resume()
            
        else:
            client.pause()

    @commands.command(aliases=["vol", "v", "V"])
    @commands.guild_only()
    @commands.check(audio_playing)
    @commands.check(in_voice_channel)
    # @commands.check(is_audio_requester)
    async def volume(self, ctx, volume: int):
        """Change the volume of currently playing audio (values 0-250)."""
        state = self.get_state(ctx.guild.id)

        # make sure volume is nonnegative
        if volume < 0:
            await ctx.send(f"Set volume to **0**")
            volume = 0

        max_vol = self.config["max_volume"]
        if max_vol > -1:  # check if max volume is set
            # clamp volume to [0, max_vol]
            if volume > max_vol:
                volume = max_vol
                await ctx.send(f"Set volume to **{max_vol}**")
            else:
                await ctx.send(f"Set volume to {volume}")

        client = ctx.guild.voice_client

        state.volume = float(volume) / 100.0
        client.source.volume = state.volume  # update the AudioSource's volume to match

    @commands.command(aliases=["s"])
    @commands.guild_only()
    async def skip(self, ctx):
        """Skips the currently playing song, or votes to skip it."""
        state = self.get_state(ctx.guild.id)
        client = ctx.guild.voice_client
        voice_run = discord.utils.get(self.bot.voice_clients, guild=ctx.guild)
        if voice_run == None:
            emBed4 = discord.Embed(color=0xff0000)
            emBed4.add_field(name='เกิดข้อผิดพลาด T_T', value='บอทไม่ได้เชื่อมต่อกับช่องเสียงอยู่')
            emBed4.set_author(name="006 music", icon_url=alert_url)
            await ctx.send(embed=emBed4, delete_after=5)
            await asyncio.sleep(5)
            await ctx.message.delete()
            return

        if voice_run.channel != ctx.author.voice.channel:
            emBed5 = discord.Embed(color=0xff0000)
            emBed5.add_field(name='เกิดข้อผิดพลาด T_T', value='คุณไม่ได้อยู่ช่องเดียวกับบอทจึงไม่สามารถใช้คำสั่งนี้ได้\n- ขณะนี้บอทกำลังอยู่ในช่อง **{0}**'.format(voice_run.channel))
            emBed5.set_author(name="006 music", icon_url=alert_url)
            await ctx.send(embed=emBed5, delete_after=10)
            await asyncio.sleep(10)
            await ctx.message.delete()
            return
        elif not voice_run.is_playing():
            emBed5 = discord.Embed(color=0xff0000)
            emBed5.add_field(name='เกิดข้อผิดพลาด T_T', value='เพลงไม่ได้เล่นอยู่จึง ข้ามไม่ได้')
            emBed5.set_author(name="006 music", icon_url=alert_url)
            await ctx.send(embed=emBed5, delete_after=10)
            await asyncio.sleep(10)
            await ctx.message.delete()
            return
        elif state.repeat == True:
            emBed5 = discord.Embed(color=0xff0000)
            emBed5.add_field(name='เกิดข้อผิดพลาด T_T', value="Can't skip song when loop is **on**")
            emBed5.set_author(name="006 music", icon_url=alert_url)
            await ctx.send(content=None, embed=emBed5, delete_after=10)
            await asyncio.sleep(10)
            await ctx.message.delete()
            return
        if ctx.channel.permissions_for(ctx.author).administrator or state.is_requester(ctx.author):
            # immediately skip if requester or admin
            emBed6 = discord.Embed(color=0xF3F4F9)
            emBed6.add_field(name='ข้ามเพลงแล้ว', value=(f'**`{ctx.author.name}`**: Skipped the song!'))
            await ctx.send(embed=emBed6)
            voice_run.stop()
            return
        elif self.config["vote_skip"]:
            # vote to skip song
            channel = client.channel
            self._vote_skip(channel, ctx.author)
            # announce vote
            users_in_channel = len([
                member for member in channel.members if not member.bot
            ])  # don't count bots
            required_votes = math.ceil(self.config["vote_skip_ratio"] * users_in_channel)
            await ctx.send(f"{ctx.author.mention} voted to skip ({len(state.skip_votes)}/{required_votes} votes)")
        else:
            raise commands.CommandError("Sorry, vote skipping is disabled.")

    @commands.command(aliases=["np"])
    @commands.guild_only()
    @commands.check(audio_playing)
    async def nowplaying(self, ctx):
        """Displays information about the current song."""
        state = self.get_state(ctx.guild.id)
        if state.repeat == True:
            message = await ctx.send("**now loop this**", embed=state.now_playing.get_embed())
            return
        else:
            message = await ctx.send("**now playing**", embed=state.now_playing.get_embed())

    @commands.command(aliases=["q", "playlist"])
    @commands.guild_only()
    @commands.check(audio_playing)
    async def queue(self, ctx):
        """Display the current play queue."""
        state = self.get_state(ctx.guild.id)
        if state.repeat == True:
            message = await ctx.send("**now loop this**", embed=state.now_playing.get_embed())
            return 
        queue = state.playlist
        # await ctx.send(embed=self._queue_text(state.playlist))
        if len(queue) > 0:
            fmt = "\n".join(f"- {index+1}. **{song.title}**"for (index, song) in enumerate(queue))
              # add individual songs
            embed2 = discord.Embed(title=f'รายการเพลงที่ยังไม่ได้เล่น - ทั้งหมด {len(queue)}', description=fmt, color=0xC1E1C1)
            await ctx.send(embed=embed2)
        else:
            await ctx.send("The play queue is empty.")

    # def _queue_text(self, queue):
    #     """Returns a block of text describing a given song queue."""
        
        

    @commands.command(aliases=["cq"])
    @commands.guild_only()
    @commands.check(audio_playing)
    # @commands.has_permissions(administrator=True)
    async def clearqueue(self, ctx):
        """Clears the play queue without leaving the channel."""
        state = self.get_state(ctx.guild.id)
        state.playlist = []
        await ctx.send("clear all queues complete ✅")

    @commands.command(aliases=["jq"])
    @commands.guild_only()
    @commands.check(audio_playing)
    # @commands.has_permissions(administrator=True)
    async def jumpqueue(self, ctx, song: int, new_index: int):
        """Moves song at an index to `new_index` in queue."""
        state = self.get_state(ctx.guild.id)  # get state for this guild
        if 1 <= song <= len(state.playlist) and 1 <= new_index:
            song = state.playlist.pop(song - 1)  # take song at index...
            state.playlist.insert(new_index - 1, song)  # and insert it.

            await ctx.send(self._queue_text(state.playlist))
        else:
            raise commands.CommandError("You must use a valid index.")

    def _queue_text(self, queue):
        """Returns a block of text describing a given song queue."""
        if len(queue) > 0:
            message = [f"{len(queue)} songs in queue:"]
            message += [
                f"  {index+1}. **{song.title}**)"for (index, song) in enumerate(queue)]  # add individual songs
            return "\n".join(message)
        else:
            return "The play queue is empty."

    @commands.command(aliases=["p"], brief="Plays audio from <url>.")
    @commands.guild_only()
    async def play(self, ctx, *, url):
        """Plays audio hosted at <url> (or performs a search for <url> and plays the first result)."""
        client = ctx.guild.voice_client
        state = self.get_state(ctx.guild.id)  # get the guild's state
        state.text_channel = ctx.channel
        channel = discord.VoiceChannel = None
        voice_run = discord.utils.get(self.bot.voice_clients, guild=ctx.guild)
        if not channel:
            try:
                channel = ctx.author.voice.channel
            except AttributeError:
                emBed5 = discord.Embed(color=0xff0000)
                emBed5.add_field(name='เกิดข้อผิดพลาด T_T', value='กรุณาเชื่อมต่อช่องเสียงก่อน')
                await ctx.send(content = None, embed=emBed5, delete_after=10)
                await asyncio.sleep(10)
                await ctx.message.delete()
                return
        voice_run = discord.utils.get(self.bot.voice_clients, guild=ctx.guild)
        if client and client.channel:
            if voice_run.channel != ctx.author.voice.channel:
                emBed5 = discord.Embed(color=0xff0000)
                emBed5.add_field(name='เกิดข้อผิดพลาด T_T', value='คุณไม่ได้อยู่ช่องเดียวกับบอทจึงไม่สามารถใช้คำสั่งนี้ได้\n- ขณะนี้บอทกำลังอยู่ในช่อง **{0}**'.format(voice_run.channel))
                emBed5.set_author(name="006 music", icon_url=alert_url)
                await ctx.send(embed=emBed5, delete_after=10)
                await asyncio.sleep(10)
                await ctx.message.delete()
                return 
            if state.repeat == True:
                emBed5 = discord.Embed(color=0xff0000)
                emBed5.add_field(name='เกิดข้อผิดพลาด T_T', value="Can't add any song when loop is **on**")
                emBed5.set_author(name="006 music", icon_url=alert_url)
                await ctx.send(content=None, embed=emBed5, delete_after=10)
                await asyncio.sleep(10)
                await ctx.message.delete()
                return 
            try:
                video = await Video.create(url, ctx.author, self.bot.loop)
            except youtube_dl.DownloadError as e:
                logging.warn(f"Error downloading song: {e} | In : {ctx.guild.name} Id :{ctx.guild.id}")
                await ctx.send(
                    "There was an error downloading your song, **sorry.**")
                return
            state.playlist.append(video)
            if not client.is_playing():
                await self._play_next(ctx, state)
            message = await ctx.send(embed=video.get_embed())
        else:
            if ctx.author.voice is not None and ctx.author.voice.channel is not None:
                channel = ctx.author.voice.channel
                try:
                    video = await Video.create(url, ctx.author, self.bot.loop)
                except youtube_dl.DownloadError as e:
                    await ctx.send(
                        "There was an error downloading your song, **sorry.**")
                    return
                client = await channel.connect()
                await ctx.guild.change_voice_state(channel=channel, self_mute=False, self_deaf=True)
                self._play_song(client, state, video)
                message = await ctx.send("", embed=video.get_embed())
                logging.info(f"Now playing '{video.title}' | In : {ctx.guild.name} Id :{ctx.guild.id}")
            else:
                raise commands.CommandError(
                    "You need to be in a voice channel to do that.")

    def _vote_skip(self, channel, member):
        """Register a vote for `member` to skip the song playing."""
        logging.info(f"{member.name} votes to skip")
        state = self.get_state(channel.guild.id)
        state.skip_votes.add(member)
        users_in_channel = len([
            member for member in channel.members if not member.bot
        ])  # don't count bots
        if (float(len(state.skip_votes)) /
                users_in_channel) >= self.config["vote_skip_ratio"]:
            # enough members have voted to skip, so skip the song
            logging.info(f"Enough votes, skipping... | In : {member.guild.name} Id :{member.guild.id}")
            channel.guild.voice_client.stop()

async def setup(bot):
    config = bot.config  # ดึง config จาก bot
    await bot.add_cog(Music(bot, config))  # ส่ง config ไปให้ Music

class GuildState:
    """Helper class managing per-guild state."""

    def __init__(self):
        self.volume = 1.0
        self.playlist = []
        self.skip_votes = set()
        self.now_playing = None
        self.repeat = False
        self.finish = True
        self.text_channel = None

    def is_requester(self, user):
        return self.now_playing and self.now_playing.requested_by == user