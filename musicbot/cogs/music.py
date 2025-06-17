import asyncio
from datetime import datetime
import math
import sys
from pytz import timezone
import logging
import discord
from discord import app_commands
from discord.ext import commands
from ..video import Video
from ..un_use.playlist import Videoplaylist
import yt_dlp as youtube_dl
import urllib

#url
alert_url = "https://i.ibb.co/ykzmssp/aleart.gif"
logo_bot = "https://i.ibb.co/6PmVgYx/logo-bot.png"

YTDL_OPTS = {
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

FFMPEG_BEFORE_OPTS = '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5'
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
        name="help",
        description="show help command"
    )
    async def _help(self, interaction: discord.Interaction):
        emBed = discord.Embed(title="**006 music help**", description="All actailable bot command", color=0xF3F4F9)
        emBed.add_field(name="-help", value="เพื่อดูว่า ณ ตอนนี้มีคำสั่งอะไรบ้าง", inline=False)
        emBed.add_field(name="-play + url หรือ ชื่อเพลง [ ย่อๆว่า : -p ]", value="เพื่อเล่นเพลง", inline=False)
        emBed.add_field(name="-skip [ ย่อๆว่า : -s ]", value="เพื่อข้ามเพลง", inline=False)
        emBed.add_field(name="-pause", value="เพื่อหยุดเล่นเพลงชั่วคราว/หรือเล่นเพลงต่อ", inline=False)
        emBed.add_field(name="-np", value="ดูเพลงที่กำลังเล่นอยู่", inline=False)
        emBed.add_field(name="-v + ค่าความดัง 0 ถึง 250", value="เพื่อเพิ่ม/ลดเสียง", inline=False)
        emBed.add_field(name="-leave [ ย่อๆว่า : -l ]", value="เพื่อให้บอทออกจากช่อง", inline=False)
        emBed.add_field(name="-bug", value="ช่องทาง report bug มาที่ผู้สร้าง", inline=False)
        emBed.add_field(name="-queue", value="เพื่อดูคิวเพลง", inline=False)
        emBed.add_field(name="-cq", value="เพื่อล้างเพลงทั้งหมดในคิว", inline=False)
        emBed.add_field(name="**หรือจะใช้ SlashCommand ก็ได้นะ**", value="SlashCommand(/) Supported", inline=False)
        emBed.set_thumbnail(url=logo_bot)
        emBed.set_footer(text="Dev. SUPANAT_hub", icon_url="https://i.ibb.co/nMCC4Dhs/avatars-Ur-ODnvl-RAOkd-T0-Rc-U89uh-A-t200x200.jpg")
        await interaction.response.send_message(embed=emBed)
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
        await interaction.response.send_message(f'{str(member.avatar)}')
    
    @app_commands.guild_only()
    @app_commands.command(
        name="play",
        description="play song by url/name"
    )
    async def _play(self, interaction: discord.Interaction, search: str):
        """Plays audio hosted at <url> (or performs a search for <url> and plays the first result)."""
        await interaction.response.defer()
        state = self.get_state(interaction.guild_id)  # get the guild's state
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
                video = Video(search, interaction.user)
            except youtube_dl.DownloadError as e:
                logging.warn(f"Error downloading song: {e} | In : {interaction.guild.name} Id :{interaction.guild_id}")
                await interaction.followup.send(content="There was an error downloading your song, **sorry.**", embed=None)
                return
            state.playlist.append(video)
            await interaction.followup.send(content=None, embed=video.get_embed())
        else:
            if interaction.user.voice is not None and interaction.user.voice.channel is not None:
                channel = interaction.user.voice.channel
                try:
                    video = Video(search, interaction.user)
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
    @app_commands.command(
        name="play-playlist",
        description="play playlist by url only."
    )
    async def _playplaylist(self, interaction: discord.Interaction, url: str):
        """Plays audio hosted at <url> (or performs a search for <url> and plays the first result)."""
        await interaction.response.send_message("**wait for it....**")
        client = interaction.guild.voice_client
        state = self.get_state(interaction.guild_id)  # get the guild's state
        channel = discord.VoiceChannel = None
        voice_run = discord.utils.get(self.bot.voice_clients, guild=interaction.guild)
        fullstring = url
        substring = "youtube.com/playlist"
        try:
            if substring in fullstring:
                pass
            else:
                emBed5 = discord.Embed(color=0xff0000)
                emBed5.add_field(name='เกิดข้อผิดพลาด T_T', value='This is not a playlist url.')
                emBed5.set_author(name="006 music", icon_url=alert_url)
                await interaction.edit_original_response(content=None, embed=emBed5)
                await asyncio.sleep(10)
                await interaction.delete_original_response()
                return
        except:
                emBed5 = discord.Embed(color=0xff0000)
                emBed5.add_field(name='เกิดข้อผิดพลาด T_T', value='This is not a playlist url.')
                emBed5.set_author(name="006 music", icon_url=alert_url)
                await interaction.edit_original_response(content=None, embed=emBed5)
                await asyncio.sleep(10)
                await interaction.delete_original_response()
                return
        status_code = urllib.request.urlopen(url).getcode()
        website_is_up = status_code == 200
        if website_is_up:
            pass
        else:
            emBed5 = discord.Embed(color=0xff0000)
            emBed5.add_field(name='เกิดข้อผิดพลาด T_T', value='This is not url.')
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
                await interaction.edit_original_response(content = None, embed=emBed5)
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
                with youtube_dl.YoutubeDL(YTDL_OPTS) as ydl:
                    info = ydl.extract_info(url, download=False)
                    video = None
                    entries = info["entries"]
                    d = len(entries)
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
                                video = await asyncio.to_thread(Video, video_url, itac)
                                state.playlist.append(video)
                                success += 1
                            except Exception as e:
                                logging.warn(f"Error downloading song: {e} | In : {interaction.guild.name} Id :{interaction.guild_id}")
                                fail += 1
                                continue
                            if (i+1) % 2 == 0 or (i+1) == d:
                                bar = make_progress_bar(i+1, d)
                                await interaction.edit_original_response(content=f"{bar} เพิ่มเพลงสำเร็จ {success} | ล้มเหลว {fail}")
            except youtube_dl.DownloadError as e:
                logging.warn(f"Error downloading song: {e} | In : {interaction.guild.name} Id :{interaction.guild_id}")
                await interaction.edit_original_response(content="There was an error downloading your song, **sorry.**", embed=None)
                return
            if state.finish == True:
                    await interaction.edit_original_response(content=f"**เพิ่มเพลงสำเร็จ {success} | ล้มเหลว {fail}**", embed=state.playlist[0].get_embed())
            else:
                emBed5 = discord.Embed(color=0xff0000)
                emBed5.add_field(name='เกิดข้อผิดพลาด T_T', value='Fail to add playlist, Try again leter.')
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
                    video = Video(url, interaction.user)
                except youtube_dl.DownloadError as e:
                    await interaction.edit_original_response(content="There was an error downloading your song, **sorry.**", embed=None)
                    return
                with youtube_dl.YoutubeDL(YTDL_OPTS) as ydl:
                    info = ydl.extract_info(url, download=False)
                    entries = info["entries"]
                    d = len(entries)
                    if d > 50:
                        emBed5 = discord.Embed(color=0xff0000)
                        emBed5.add_field(name='เกิดข้อผิดพลาด T_T', value='ไม่สามารถเล่นได้ เนื่องจากมีวิดีโอในเพลลิสต์มากกว่า 50 ')
                        emBed5.set_author(name="006 music", icon_url=alert_url)
                        await interaction.edit_original_response(content=None, embed=emBed5)
                        await asyncio.sleep(10)
                        await interaction.delete_original_response()
                        return
                client = await channel.connect()
                await interaction.guild.change_voice_state(channel=channel, self_mute=False, self_deaf=True)
                self._play_song(client, state, video)
                try:
                    with youtube_dl.YoutubeDL(YTDL_OPTS) as ydl:
                        info = ydl.extract_info(url, download=False)
                        entries = info["entries"]
                        d = len(entries)
                        video = None
                    if "_type" in info and info["_type"] == "playlist":
                        await interaction.edit_original_response(content="**processing...**")
                        itac = interaction.user
                        success = 1
                        fail = 0
                        for i, entry in enumerate(entries[1:], start=1):
                            video_url = entry.get('webpage_url') or entry.get('url')
                            if not video_url:
                                continue
                            try:
                                video = await asyncio.to_thread(Video, video_url, itac)
                                state.playlist.append(video)
                                success += 1
                            except Exception as e:
                                logging.warn(f"Error downloading song: {e} | In : {interaction.guild.name} Id :{interaction.guild_id}")
                                fail += 1
                                continue
                            if (i+1) % 2 == 0 or (i+1) == d:
                                bar = make_progress_bar(i+1, d)
                                await interaction.edit_original_response(content=f"{bar} เพิ่มเพลงสำเร็จ {success} | ล้มเหลว {fail}")
                except:
                    pass
                if state.finish == True:
                    await interaction.edit_original_response(content=f"**เพิ่มเพลงสำเร็จ {success} | ล้มเหลว {fail}**", embed=state.now_playing.get_embed())
                else:
                    emBed5 = discord.Embed(color=0xff0000)
                    emBed5.add_field(name='เกิดข้อผิดพลาด T_T', value='Fail to add playlist, Try again leter.')
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

    @commands.command(aliases=["h", "H"])
    async def help(self, ctx):
        emBed = discord.Embed(title="**006 music help**", description="All actailable bot command", color=0xF3F4F9)
        emBed.add_field(name="-help", value="เพื่อดูว่า ณ ตอนนี้มีคำสั่งอะไรบ้าง", inline=False)
        emBed.add_field(name="-play + url หรือ ชื่อเพลง [ ย่อๆว่า : -p ]", value="เพื่อเล่นเพลง", inline=False)
        emBed.add_field(name="-skip [ ย่อๆว่า : -s ]", value="เพื่อข้ามเพลง", inline=False)
        emBed.add_field(name="-pause", value="เพื่อหยุดเล่นเพลงชั่วคราว/หรือเล่นเพลงต่อ", inline=False)
        emBed.add_field(name="-np", value="ดูเพลงที่กำลังเล่นอยู่", inline=False)
        emBed.add_field(name="-v + ค่าความดัง 0 ถึง 250", value="เพื่อเพิ่ม/ลดเสียง", inline=False)
        emBed.add_field(name="-leave [ ย่อๆว่า : -l ]", value="เพื่อให้บอทออกจากช่อง", inline=False)
        emBed.add_field(name="-bug", value="ช่องทาง report bug มาที่ผู้สร้าง", inline=False)
        emBed.add_field(name="-queue", value="เพื่อดูคิวเพลง", inline=False)
        emBed.add_field(name="-cq", value="เพื่อล้างเพลงทั้งหมดในคิว", inline=False)
        emBed.add_field(name="**หรือจะใช้ SlashCommand ก็ได้นะ**", value="SlashCommand(/) Supported", inline=False)
        emBed.set_thumbnail(url=logo_bot)
        emBed.set_footer(text="Dev. SUPANAT_hub", icon_url="https://i1.sndcdn.com/avatars-UrODnvlRAOkdT0Rc-U89uhA-t200x200.jpg")
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
                video = Video(url, ctx.author)
            except youtube_dl.DownloadError as e:
                logging.warn(f"Error downloading song: {e} | In : {ctx.guild.name} Id :{ctx.guild.id}")
                await ctx.send(
                    "There was an error downloading your song, **sorry.**")
                return
            state.playlist.append(video)
            message = await ctx.send(embed=video.get_embed())
        else:
            if ctx.author.voice is not None and ctx.author.voice.channel is not None:
                channel = ctx.author.voice.channel
                try:
                    video = Video(url, ctx.author)
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


    def _play_song(self, client, state, song):
        state.now_playing = song
        state.skip_votes = set()  # clear skip votes
        source = discord.PCMVolumeTransformer(
            discord.FFmpegPCMAudio(song.stream_url, before_options=FFMPEG_BEFORE_OPTS), volume=state.volume)
        logging.info(f"playing : {song.title} vc : {client}")
#         print(f'''------------------------------------------------
#     song.stream_url = {song.stream_url}
# -------------------------------------------------
#               '''
#               )

        def after_playing(err):
            if state.repeat == True:
                self._play_song(client, state, song)
                return
            if len(state.playlist) > 0:
                next_song = state.playlist.pop(0)
                self._play_song(client, state, next_song)
            else:
                if len(state.playlist) <= 0:
                    asyncio.run_coroutine_threadsafe(client.disconnect(),self.bot.loop)
                else:
                    pass
        client.play(source, after=after_playing)

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

    def is_requester(self, user):
        return self.now_playing.requested_by == user