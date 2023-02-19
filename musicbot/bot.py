import discord
import logging
import os
import sys
from discord.ext import commands, tasks
from discord import Intents
from discord import app_commands
from .cogs import music, error, meta, chord
import aiohttp
import asyncio
from . import config
cfg = config.load_config()
cogs = [music.Music, error.CommandErrorHandler, meta.Meta, chord.Chord]
class Mybot(commands.Bot):
    def __init__(self):
        super().__init__(
            command_prefix = cfg["prefix"],
            intents = Intents.all(),
            help_command=None,
            application_id = cfg["app_id"]
        )
    
    async def setup_hook(self):
        # await bot.remove_cog("Meta")
        # await bot.remove_cog("Music")
        # await bot.remove_cog("Chord")
        # await bot.remove_cog("CommandErrorHandler")
        logging.info(f"Cogs syncing....")
        await bot.tree.sync() #dumb way to sync but worked.
        for cog in cogs:
            await bot.add_cog(cog(bot, cfg))
        await bot.tree.sync()
        logging.info(f"Cogs synced.")
        
    async def on_ready(self):
        status_task.start()
        logging.info(f"Logged in as {bot.user}")

bot = Mybot()

@bot.event
async def on_guild_join(guild):
    await bot.change_presence(activity=discord.Game(name=f"-help || {len(bot.guilds)} servers."))

@tasks.loop()
async def status_task():
        await bot.change_presence(activity=discord.Game(name=f"-help || {len(bot.guilds)} servers."))
        await asyncio.sleep(60)

def run():
    bot.run(cfg["token"])