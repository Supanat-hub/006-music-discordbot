import discord
import logging
import asyncio
from discord.ext import commands, tasks
from discord import Intents, app_commands
from .cogs import music, error, meta, chord
from . import config

cfg = config.load_config()
# cogs = [music.Music, error.CommandErrorHandler, meta.Meta, chord.Chord]

class Mybot(commands.Bot):
    def __init__(self):
        super().__init__(
            command_prefix=cfg["prefix"],
            intents=Intents.all(),
            help_command=None,
            application_id=cfg["app_id"]
        )
        self.synced = False  # ป้องกันการ sync ซ้ำ
        self.config = config.load_config()

    async def setup_hook(self):
        logging.info("Loading Cogs...")
        cogs = ["musicbot.cogs.music", "musicbot.cogs.meta", "musicbot.cogs.error", "musicbot.cogs.chord"]  # รายชื่อ Cog
        for cog in cogs:
            await self.load_extension(cog)
            # await self.add_cog(cog(self, cfg))
        logging.info("Cogs Loaded.")

    async def on_ready(self):
        if not self.synced:
            await self.tree.sync()
            self.synced = True
            logging.info("Commands synced.")
        status_task.start()
        logging.info(f"Logged in as {self.user}")

bot = Mybot()

@bot.event
async def on_guild_join(guild):
    await bot.change_presence(activity=discord.Game(name=f"-help || {len(bot.guilds)} servers."))

@tasks.loop(seconds=60)
async def status_task():
    await bot.change_presence(activity=discord.Game(name=f"-help || {len(bot.guilds)} servers."))

@app_commands.context_menu(name="Get User Avatar")
async def avatar(interaction: discord.Interaction, user: discord.User):
    embed = discord.Embed(title="Avatar", description=f"- {user.mention}")
    embed.set_image(url=user.avatar.url)
    await interaction.response.send_message(embed=embed)

bot.tree.add_command(avatar)

def run():
    bot.run(cfg["token"], reconnect=True)
