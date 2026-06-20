import re
import logging
import discord
from discord import app_commands
from discord.ext import commands
import aiohttp
from bs4 import BeautifulSoup
from urlextract import URLExtract

# User agent to prevent Google blocking
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

async def fetch_html(url: str) -> str | None:
    """Fetch HTML content asynchronously using aiohttp."""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=HEADERS, timeout=10) as response:
                if response.status == 200:
                    return await response.text()
    except Exception as e:
        logging.error(f"Error fetching HTML from {url}: {e}")
    return None

class Chord(commands.Cog):
    def __init__(self, bot: commands.Bot, config) -> None:
        self.bot = bot
        self.config = config
        self.states = {}

    @app_commands.guild_only()
    @app_commands.command(
        name="dochord",
        description="Chord for song.(Beta)"
    )
    async def _dochord(self, interaction: discord.Interaction, song: str):
        await interaction.response.defer()
        
        search_term = f"{song}+dochord"
        search_url = f"https://www.google.com/search?q={search_term}&ie=UTF-8"
        
        content = await fetch_html(search_url)
        if not content:
            await interaction.followup.send(content="Can't connect to search engine. Try again later.")
            return

        soup = BeautifulSoup(content, "html.parser")
        results = soup.find_all("a")
        
        extractor = URLExtract()
        urls = extractor.find_urls(str(results))
        
        if len(urls) < 2:
            await interaction.followup.send(content="Can't find chords for this song.")
            return

        # clean URL
        url = str(urls[1]).replace("&amp", "")
        if "google.com" in url:
            # find first non-google link
            for u in urls:
                if "google.com" not in u:
                    url = u
                    break

        if url == "https://www.dochord.com/" or "dochord.com" not in url:
            await interaction.followup.send(content="Can't find this song on dochord.")
            return

        # Fetch chord page html
        chord_html = await fetch_html(url)
        if not chord_html:
            await interaction.followup.send(content="Failed to retrieve chords from Dochord.")
            return

        soup_chord = BeautifulSoup(chord_html, "html.parser")
        div = soup_chord.find("div", class_="row main_chord main_chord_content")
        if div is None:
            await interaction.followup.send(content="Error parsing chords for this song.")
            return

        try:
            rp = str(div).replace("          ", "&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;")
            rp = rp + '<link rel="stylesheet" href="https://drive.google.com/uc?export=view&id=1JlGTCRiR1XieWm8Lf6WQftQUL1iXABLY">'
        except Exception:
            await interaction.followup.send(content="Error formatting chord page.")
            return

        # Load API keys from config (under [chord] section or fallback)
        chord_cfg = self.config.get("chord", {})
        api_user_id = chord_cfg.get("hcti_api_user_id")
        api_key = chord_cfg.get("hcti_api_key")

        # Fallback if HCTI API keys are placeholders or not set
        if not api_user_id or not api_key or api_user_id == "id" or api_key == "key":
            await interaction.followup.send(
                content=f"🎵 **{song}**\nดูคอร์ดเพลงได้ที่นี่: {url}\n*(หมายเหตุ: แอดมินยังไม่ได้ตั้งค่า HCTI API Key เพื่อแสดงผลเป็นรูปภาพ)*"
            )
            return

        try:
            HCTI_API_ENDPOINT = "https://hcti.io/v1/image"
            data = {
                'html': rp,
                'css': "https://drive.google.com/uc?export=view&id=1JlGTCRiR1XieWm8Lf6WQftQUL1iXABLY",
                'google_fonts': "Roboto"
            }

            async with aiohttp.ClientSession() as session:
                auth = aiohttp.BasicAuth(api_user_id, api_key)
                async with session.post(HCTI_API_ENDPOINT, data=data, auth=auth) as resp:
                    if resp.status in (200, 201):
                        image_data = await resp.json()
                        image_url = image_data.get('url')
                        
                        emBed = discord.Embed(
                            title=f"**{song}**", url=image_url, description="ภาพคอร์ดเพลง", color=0xF3F4F9
                        )
                        emBed.set_image(url=image_url)
                        emBed.set_author(name="006 music", icon_url="https://i.ibb.co/6s134j9/musicrun.gif")
                        await interaction.followup.send(embed=emBed)
                    else:
                        raise Exception(f"HCTI API returned status {resp.status}")
        except Exception as e:
            logging.error(f"Error rendering image with HCTI: {e}")
            await interaction.followup.send(
                content=f"🎵 **{song}**\nดูคอร์ดเพลงได้ที่นี่: {url}\n*(หมายเหตุ: ไม่สามารถโหลดรูปภาพได้เนื่องจาก API ลิมิตหมดหรือตั้งค่าผิดพลาด)*"
            )

    @app_commands.guild_only()
    @app_commands.command(
        name="tap",
        description="tap guitar for song."
    )
    async def _tap(self, interaction: discord.Interaction, song: str):
        await interaction.response.defer()

        search_term = f"chordtaps {song}"
        search_url = f"https://www.google.com/search?q={search_term}&ie=UTF-8"
        
        content = await fetch_html(search_url)
        if not content:
            await interaction.followup.send(content="Can't connect to search engine.")
            return

        soup = BeautifulSoup(content, "html.parser")
        results = soup.find_all("a")
        
        extractor = URLExtract()
        urls = extractor.find_urls(str(results))
        
        if len(urls) < 2:
            await interaction.followup.send(content="Can't find tap guitar for this song.")
            return

        # find first non-google link
        url = str(urls[1]).replace("&amp", "")
        for u in urls:
            if "google.com" not in u:
                url = u
                break
                
        await interaction.followup.send(content=f"🎸 **Guitar Tap สำหรับเพลง {song}**:\n{url}")

async def setup(bot):
    config = bot.config
    await bot.add_cog(Chord(bot, config))
