import discord
from discord import app_commands
from discord.ext import commands
import requests
from bs4 import BeautifulSoup
from html2image import Html2Image
from PIL import Image
from urlextract import URLExtract
import datetime
import pdfcrowd

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
        url = f"https://www.google.com/search?q={search_term}+dochord&oq={search_term}&aqs=chrome.0.69i59l2j46i512j0i512l2j69i61l3.5781j0j1&sourceid=chrome&ie=UTF-8"
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
            rp = str(div).replace("          ", "&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;")
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

            data = { 'html': rp,
                    'css': "https://drive.google.com/uc?export=view&id=1JlGTCRiR1XieWm8Lf6WQftQUL1iXABLY",
                    'google_fonts': "Roboto" }

            image = requests.post(url = HCTI_API_ENDPOINT, data = data, auth=(HCTI_API_USER_ID, HCTI_API_KEY))
            emBed = discord.Embed(title=f"**{song}**",url=image.json()['url'], description="ภาพคอร์ดเพลง", color=0xF3F4F9)
            emBed.set_image(url=image.json()['url'])
            emBed.set_author(name="006 music", icon_url="https://cdn.discordapp.com/emojis/1033702427892920331.gif")
            print(url)
            print(rp)
            await interaction.followup.send(embed=emBed)
        except:
            try:
                suffix = datetime.datetime.now().strftime("%y%m%d_%H%M%S")
                # create the API client instance
                client = pdfcrowd.HtmlToImageClient('SUPANAT_hub', '1dc23428d481e9d8fba238d39d2b29d7')

                # configure the conversion
                client.setOutputFormat('png')

                # run the conversion and write the result to a file
                client.convertStringToFile(rp, f"chord_img/{suffix}.png")
                await interaction.followup.send(content=f"**{song}**\nใช้apiสำรอง เนื่องจากapiหลักเต็ม  \n`อาจทำให้มีบัคเล็กน้อย`", file=discord.File(f"chord_img/{suffix}.png"))
            except pdfcrowd.Error as why:
                # report the error
                print('Pdfcrowd Error: {}\n'.format(why))
                await interaction.followup.send(content="Sorry, the api has reached its limit for this month.")
                return
            