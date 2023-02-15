import re
import discord
from discord import app_commands
from discord.ext import commands
import requests
from bs4 import BeautifulSoup
import datetime
from urlextract import URLExtract


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
        url = f"https://www.google.com/search?q={search_term}&ie=UTF-8"
        response = requests.get(url)
        content = response.text
        soup = BeautifulSoup(content, "html.parser")
        results = soup.find_all("a")[16] # Each computer will use this value differently.
        extractor = URLExtract()
        urls = extractor.find_urls(str(results))
        url = str(urls[0]).replace("&amp", "")
        if url == "https://www.dochord.com/":
            await interaction.followup.send(content="Can't find this song.")
            return
        # Make a request to the webpage
        response = requests.get(url)
        # Parse the HTML of the webpage
        soup = BeautifulSoup(response.text, "html.parser")
        # Find the first `div` element with the class "row main_chord main_chord_content"
        div = soup.find("div", class_="row main_chord main_chord_content")
        if div == None:
            await interaction.followup.send(content="Error with this song.")
            return
        try:
            rp = str(div).replace("          ",
                                  "&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;")
        except:
            pass
        try:
            rp = rp + '<link rel="stylesheet" href="https://drive.google.com/uc?export=view&id=1JlGTCRiR1XieWm8Lf6WQftQUL1iXABLY">'
        except:
            await interaction.followup.send(content="Error with this song.")
            return

        try:
            HCTI_API_ENDPOINT = "https://hcti.io/v1/image"
            # Retrieve these from https://htmlcsstoimage.com/dashboard
            HCTI_API_USER_ID = 'id'
            HCTI_API_KEY = 'key'

            data = {'html': rp,
                    'css': "https://drive.google.com/uc?export=view&id=1JlGTCRiR1XieWm8Lf6WQftQUL1iXABLY",
                     'google_fonts': "Roboto"}

            image = requests.post(url=HCTI_API_ENDPOINT, data=data, auth=(
                HCTI_API_USER_ID, HCTI_API_KEY))
            emBed = discord.Embed(
                title=f"**{song}**", url=image.json()['url'], description="ภาพคอร์ดเพลง", color=0xF3F4F9)
            emBed.set_image(url=image.json()['url'])
            emBed.set_author(name="006 music",
                             icon_url="https://i.ibb.co/6s134j9/musicrun.gif")
            print(url)
            await interaction.followup.send(embed=emBed)
        except:
            await interaction.followup.send(content="Sorry, the api has reached its limit for this month.")
            return

    @app_commands.guild_only()
    @app_commands.command(
        name="lyrics",
        description="Lyrics for song."
    )
    async def _lyrics(self, interaction: discord.Interaction, song: str):
        await interaction.response.defer()

        search_term = f"{song}+chordzaa"
        url = f"https://www.google.com/search?q={search_term}&ie=UTF-8"
        response = requests.get(url)
        content = response.text
        soup = BeautifulSoup(content, "html.parser")
        
        try:
            results = soup.find_all("a")[16] # Each computer will use this value differently.
            extractor = URLExtract()
            urls = extractor.find_urls(str(results))
            url = str(urls[0]).replace(".html&amp", ".html")
            url = url.replace("%25", "%")
        except:
            await interaction.followup.send(content="Can't find this, Try again later.")
            return
        if url == "https://www.chordzaa.com/":
            await interaction.followup.send(content="Can't find this song.")
            return
        response = requests.get(url)
        soup = BeautifulSoup(response.text, "html.parser")
        basename = "lyrics"
        suffix = datetime.datetime.now().strftime("%y%m%d_%H%M%S")
        filename = "_".join([basename, suffix])
        try:
            text = soup.find("div", id="lyric_r")
            text = str(text)
            retag = re.compile('<.*?>')
            output = retag.sub("", text)
            with open(f"txt/{filename}.txt", "w", encoding="utf-8") as f:
                    f.write(output)
            await interaction.followup.send(file=discord.File(f"txt/{filename}.txt"))
        except:
            await interaction.followup.send(content="Can't find this, Try again later.")
            return