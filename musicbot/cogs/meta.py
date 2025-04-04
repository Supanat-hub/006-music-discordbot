from discord.ext import commands
import discord
from datetime import datetime
from .. import util


class Meta(commands.Cog):
    """Commands relating to the bot itself."""

    def __init__(self, bot, config):
        self.bot = bot
        self.start_time = datetime.now()
        self.config = config

    @commands.command()
    async def uptime(self, ctx):
        """Tells how long the bot has been running."""
        uptime_seconds = round(
            (datetime.now() - self.start_time).total_seconds())
        await ctx.send(f"Current Uptime: {util.format_seconds(uptime_seconds)}"
                       )

    @commands.command()
    async def text_test(self, ctx):
        await ctx.send("<a:C_U_M:967790150094561310>")
async def setup(bot):
    config = bot.config
    await bot.add_cog(Meta(bot, config))
