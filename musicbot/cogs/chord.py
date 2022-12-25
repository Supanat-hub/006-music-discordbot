import cv2
import requests
from bs4 import BeautifulSoup
from urlextract import URLExtract
from PIL import Image
from html2image import Html2Image
import discord
from discord import app_commands
from discord.ext import commands
import pyppeteer

class Chord(commands.Cog):
    def __init__(self, bot: commands.Bot, config) -> None:
        self.bot = bot
        self.config = config
        self.states = {}
        self.filename = 1
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
        # Launch a browser
        browser = await pyppeteer.launch()
        # Open a new page
        page = await browser.newPage()
        await page.setViewport({'width': 1800, 'height': 3300})
        # Navigate to a website
        await page.goto(url)
        # Capture a screenshot of the page
        screenshot = await page.screenshot()
        # Save the screenshot to a file
        with open(f'chord_img/{self.filename}.png', 'wb') as f:
            f.write(screenshot)
        # Close the browser
        await browser.close()
        # Capture the image using OpenCV
        img = cv2.imread(f"chord_img/{self.filename}.png")
        # Convert the image to a Pillow image object
        pil_img = Image.fromarray(img)
        # Crop the image using the Pillow library
        cropped_img = pil_img.crop((0, 2300, 1800, 3300))
        # Save the cropped image
        cropped_img.save(f"chord_img/{self.filename}.jpg")
        await interaction.followup.send(content=f"**คอร์ด {song}**" ,file=discord.File(f"chord_img/{self.filename}.jpg"))
        #if file > 20 overwrite file from 1.anytypefile
        if self.filename > 20:
            self.filename = 1
        else:
            self.filename += 1