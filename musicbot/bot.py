# import discord
# import logging
# import asyncio
# from discord.ext import commands, tasks
# from discord import Intents, app_commands
# from .cogs import music, error, meta, chord
# from . import config

# logo_bot = "https://i.ibb.co/6PmVgYx/logo-bot.png"
# cfg = config.load_config()
# # cogs = [music.Music, error.CommandErrorHandler, meta.Meta, chord.Chord]

# class Mybot(commands.Bot):
#     def __init__(self):
#         super().__init__(
#             command_prefix=cfg["prefix"],
#             intents=Intents.all(),
#             help_command=None,
#             application_id=cfg["app_id"]
#         )
#         self.synced = False  # ป้องกันการ sync ซ้ำ
#         self.config = config.load_config()

#     async def setup_hook(self):
#         logging.info("Loading Cogs...")
#         cogs = ["musicbot.cogs.music", "musicbot.cogs.meta", "musicbot.cogs.error", "musicbot.cogs.chord"]  # รายชื่อ Cog
#         for cog in cogs:
#             await self.load_extension(cog)
#             # await self.add_cog(cog(self, cfg))
#         logging.info("Cogs Loaded.")

#     async def on_ready(self):
#         if not self.synced:
#             await self.tree.sync()
#             self.synced = True
#             logging.info("Commands synced.")
#         status_task.start()
#         logging.info(f"Logged in as {self.user}")

# bot = Mybot()

# @bot.event
# async def on_guild_join(guild):
#     await bot.change_presence(activity=discord.Game(name=f"-help || {len(bot.guilds)} servers."))

# @tasks.loop(seconds=60)
# async def status_task():
#     await bot.change_presence(activity=discord.Game(name=f"-help || {len(bot.guilds)} servers."))

# @bot.command(aliases=["h", "H"])
# async def help(ctx):
#     emBed = discord.Embed(title="**006 music help**", description="All actailable bot command", color=0xF3F4F9)
#     emBed.add_field(name="-help", value="เพื่อดูว่า ณ ตอนนี้มีคำสั่งอะไรบ้าง", inline=False)
#     emBed.add_field(name="-play + url หรือ ชื่อเพลง [ ย่อๆว่า : -p ]", value="เพื่อเล่นเพลง", inline=False)
#     emBed.add_field(name="-skip [ ย่อๆว่า : -s ]", value="เพื่อข้ามเพลง", inline=False)
#     emBed.add_field(name="-pause", value="เพื่อหยุดเล่นเพลงชั่วคราว/หรือเล่นเพลงต่อ", inline=False)
#     emBed.add_field(name="-np", value="ดูเพลงที่กำลังเล่นอยู่", inline=False)
#     emBed.add_field(name="-v + ค่าความดัง 0 ถึง 250", value="เพื่อเพิ่ม/ลดเสียง", inline=False)
#     emBed.add_field(name="-leave [ ย่อๆว่า : -l ]", value="เพื่อให้บอทออกจากช่อง", inline=False)
#     emBed.add_field(name="-bug", value="ช่องทาง report bug มาที่ผู้สร้าง", inline=False)
#     emBed.add_field(name="-queue", value="เพื่อดูคิวเพลง", inline=False)
#     emBed.add_field(name="-cq", value="เพื่อล้างเพลงทั้งหมดในคิว", inline=False)
#     emBed.add_field(name="**หรือจะใช้ SlashCommand ก็ได้นะ**", value="SlashCommand(/) Supported", inline=False)
#     emBed.set_thumbnail(url=logo_bot)
#     emBed.set_footer(text="Dev. SUPANAT_hub", icon_url="https://i1.sndcdn.com/avatars-UrODnvlRAOkdT0Rc-U89uhA-t200x200.jpg")
#     await ctx.send(embed=emBed)

# @app_commands.command(
#         name="help",
#         description="show help command"
#     )
# async def _help(interaction: discord.Interaction):
#     emBed = discord.Embed(title="**006 music help**", description="All actailable bot command", color=0xF3F4F9)
#     emBed.add_field(name="-help", value="เพื่อดูว่า ณ ตอนนี้มีคำสั่งอะไรบ้าง", inline=False)
#     emBed.add_field(name="-play + url หรือ ชื่อเพลง [ ย่อๆว่า : -p ]", value="เพื่อเล่นเพลง", inline=False)
#     emBed.add_field(name="-skip [ ย่อๆว่า : -s ]", value="เพื่อข้ามเพลง", inline=False)
#     emBed.add_field(name="-pause", value="เพื่อหยุดเล่นเพลงชั่วคราว/หรือเล่นเพลงต่อ", inline=False)
#     emBed.add_field(name="-np", value="ดูเพลงที่กำลังเล่นอยู่", inline=False)
#     emBed.add_field(name="-v + ค่าความดัง 0 ถึง 250", value="เพื่อเพิ่ม/ลดเสียง", inline=False)
#     emBed.add_field(name="-leave [ ย่อๆว่า : -l ]", value="เพื่อให้บอทออกจากช่อง", inline=False)
#     emBed.add_field(name="-bug", value="ช่องทาง report bug มาที่ผู้สร้าง", inline=False)
#     emBed.add_field(name="-queue", value="เพื่อดูคิวเพลง", inline=False)
#     emBed.add_field(name="-cq", value="เพื่อล้างเพลงทั้งหมดในคิว", inline=False)
#     emBed.add_field(name="**หรือจะใช้ SlashCommand ก็ได้นะ**", value="SlashCommand(/) Supported", inline=False)
#     emBed.set_thumbnail(url=logo_bot)
#     emBed.set_footer(text="Dev. SUPANAT_hub", icon_url="https://i.ibb.co/nMCC4Dhs/avatars-Ur-ODnvl-RAOkd-T0-Rc-U89uh-A-t200x200.jpg")
#     await interaction.response.send_message(embed=emBed)

# @app_commands.context_menu(name="Get User Avatar")
# async def avatar(interaction: discord.Interaction, user: discord.User):
#     embed = discord.Embed(title="Avatar", description=f"- {user.mention}")
#     embed.set_image(url=user.avatar.url)
#     await interaction.response.send_message(embed=embed)

# bot.tree.add_command(_help)
# bot.tree.add_command(avatar)

# def run():
#     bot.run(cfg["token"], reconnect=True)


#########################################################

import discord
import logging
from discord.ext import commands, tasks
from discord import Intents, app_commands
from . import config

CFG = config.load_config()

class Mybot(commands.Bot):
    def __init__(self):
        # intents = discord.Intents.default()
        # intents.message_content = True  # จำเป็นสำหรับอ่านข้อความ -p ...
        # intents.members = True          # จำเป็นสำหรับ on_guild_join หรือดึงรูป user
        # # intents.presences = True      # ถ้าไม่ได้เช็คสถานะ online/offline ของคนอื่น ปิดไว้ช่วยให้ลื่นขึ้น

        super().__init__(
            command_prefix=CFG["prefix"],
            intents=Intents.all(),
            help_command=None,
            application_id=CFG["app_id"]
        )
        self.config = CFG
                    
    async def setup_hook(self):
        logging.info("Loading Cogs...")
        cogs = ["musicbot.cogs.music", "musicbot.cogs.meta", "musicbot.cogs.error", "musicbot.cogs.chord"]
        for ext in cogs:
            try:
                await self.load_extension(ext)
                logging.info(f"Loaded extension: {ext}")
            except Exception as e:
                logging.error(f"Failed to load extension {ext}: {e}")
        
        self.status_task.start() 
        logging.info("Setup complete.")

    async def on_ready(self):
        logging.info(f"Logged in as {self.user} (ID: {self.user.id})")

    async def on_guild_join(self, guild):
        await self.change_presence(activity=discord.Game(name=f"-help || {len(self.guilds)} servers."))

    @tasks.loop(seconds=60)
    async def status_task(self):
        await self.change_presence(activity=discord.Game(name=f"-help || {len(self.guilds)} servers."))

    @status_task.before_loop
    async def before_status_task(self):
        await self.wait_until_ready()

# สร้าง instance ของบอท
bot = Mybot()

@bot.hybrid_command(name="help", description="Show help command")
async def help_command(ctx):
    logo_bot = "https://i.ibb.co/6PmVgYx/logo-bot.png"
    emBed = discord.Embed(title="**006 music help**", description="All actailable bot command", color=0xF3F4F9)
    emBed.add_field(name="help", value="เพื่อดูว่า ณ ตอนนี้มีคำสั่งอะไรบ้าง", inline=False)
    emBed.add_field(name="play + url หรือ ชื่อเพลง [ ย่อๆว่า : -p ]", value="เพื่อเล่นเพลง", inline=False)
    emBed.add_field(name="skip [ ย่อๆว่า : -s ]", value="เพื่อข้ามเพลง", inline=False)
    emBed.add_field(name="pause", value="เพื่อหยุดเล่นเพลงชั่วคราว/หรือเล่นเพลงต่อ", inline=False)
    emBed.add_field(name="np", value="ดูเพลงที่กำลังเล่นอยู่", inline=False)
    emBed.add_field(name="volume + ค่าความดัง 0 ถึง 250", value="เพื่อเพิ่ม/ลดเสียง", inline=False)
    emBed.add_field(name="leave [ ย่อๆว่า : -l ]", value="เพื่อให้บอทออกจากช่อง", inline=False)
    emBed.add_field(name="bug", value="ช่องทาง report bug มาที่ผู้สร้าง", inline=False)
    emBed.add_field(name="queue", value="เพื่อดูคิวเพลง", inline=False)
    emBed.add_field(name="cq", value="เพื่อล้างเพลงทั้งหมดในคิว", inline=False)
    emBed.add_field(name="**หรือจะใช้ SlashCommand ก็ได้นะ**", value="SlashCommand(/) Supported", inline=False)
    emBed.set_thumbnail(url=logo_bot)
    emBed.set_footer(text="Dev. SUPANAT_hub", icon_url="https://i1.sndcdn.com/avatars-UrODnvlRAOkdT0Rc-U89uhA-t200x200.jpg")
    
    await ctx.send(embed=emBed)

@bot.tree.context_menu(name="Get User Avatar")
async def avatar(interaction: discord.Interaction, user: discord.User):
    embed = discord.Embed(title="Avatar", description=f"- {user.mention}")
    if user.avatar:
        embed.set_image(url=user.avatar.url)
    else:
        embed.description += "\nNo avatar set."
    await interaction.response.send_message(embed=embed)

# --- คำสั่ง Sync ---
@bot.command()
@commands.is_owner()
async def sync(ctx):
    await ctx.send("Syncing commands...")
    synced = await bot.tree.sync()
    await ctx.send(f"Synced {len(synced)} commands globally.")

def run():
    bot.run(CFG["token"], reconnect=True)