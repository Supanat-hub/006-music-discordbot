import discord
import logging
import sys
from discord.ext import commands, tasks
from discord import Intents
from discord.ext.commands import Bot
from discord_slash import SlashCommand, SlashContext
from .cogs import music, error, meta
from . import config
import asyncio


cfg = config.load_config()

bot = commands.Bot(command_prefix=cfg["prefix"], help_command=None)
slash = SlashCommand(bot, sync_commands=True, sync_on_cog_reload=True)




@bot.event
async def on_ready():
    logging.info(f"Logged in as {bot.user.name}")
    status_task.start()

@tasks.loop()
async def status_task():
        await bot.change_presence(activity=discord.Game(name=f"-help || {len(bot.guilds)} servers."))
        await asyncio.sleep(60)

@bot.event
async def on_guild_join(guild):
    await bot.change_presence(activity=discord.Game(name=f"-help || {len(bot.guilds)} servers."))
    


COGS = [music.Music, error.CommandErrorHandler, meta.Meta]


def add_cogs(bot):
    for cog in COGS:
        bot.add_cog(cog(bot, cfg))

def run():
    add_cogs(bot)
    if cfg["token"] == "":
        raise ValueError(
            "No token has been provided. Please ensure that config.toml contains the bot token."
        )
        sys.exit(1)
    bot.run(cfg["token"])
