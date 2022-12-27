import discord
from discord import app_commands
from discord.ext import commands
import requests
from bs4 import BeautifulSoup
from html2image import Html2Image
from PIL import Image
from urlextract import URLExtract
import datetime

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
        search_term = f"{song} dochord.com"
        url = f"https://www.google.com/search?q={search_term}"
        response = requests.get(url)
        content = response.text
        soup = BeautifulSoup(content, "html.parser")
        results = soup.find_all("a")[16]
        extractor = URLExtract()
        urls = extractor.find_urls(str(results))
        url = str(urls[0]).replace("&amp", "")
        if url == "https://www.dochord.com/":
            await interaction.followup.send(content="Can't find this song.")
            return
        #name gennerate
        suffix = datetime.datetime.now().strftime("%y%m%d_%H%M%S")
        # Make a request to the webpage
        response = requests.get(url)
        # Parse the HTML of the webpage
        soup = BeautifulSoup(response.text, "html.parser")
        # Find the first `div` element with the class "row main_chord main_chord_content"
        div = soup.find("div", class_="row main_chord main_chord_content")
        hiv = Html2Image(output_path="img")
        rp = str(div).replace("          ", "&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;")
        rp = rp + '<link rel="stylesheet" href="index.css">'
        pic = hiv.screenshot(html_str=rp,css_file="index.css" , size=(1200, 1400), save_as=f"{suffix}.png")

        # Load the image
        image = Image.open(f'img/{suffix}.png')
        # Convert the image to RGBA format
        image = image.convert('RGBA')

        # Get the bounding box of the non-transparent part of the image
        bbox = image.getbbox()

        # Crop the image using the bounding box
        cropped_image = image.crop(bbox)

        # Save the cropped image
        cropped_image.save(f'img/cropped_{suffix}.png')
        await interaction.followup.send(content=f"**คอร์ด {song}**" ,file=discord.File(f"img/cropped_{suffix}.png"))
    