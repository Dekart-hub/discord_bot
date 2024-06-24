import os
import discord
from discord.ext import commands
from dotenv import load_dotenv


def run_bot():
    intents = discord.Intents.default()
    intents.message_content = True
    bot = commands.Bot(command_prefix='!', intents=intents)

    @bot.event
    async def setup_hook():
        for filename in os.listdir('./cogs'):
            if filename.endswith('.py'):
                await bot.load_extension(f'cogs.{filename[:-3]}')
                print(f"Loading Cog: {filename[:-3]}")

    @bot.event
    async def on_ready():
        print('Logged on')

    @bot.command(name="sync")
    async def sync(ctx):
        if ctx.author.id == int(os.getenv("ADMIN_ID")):
            await bot.tree.sync()
            print("Synced!")
        else:
            await ctx.send("ZHOPA")

    load_dotenv()
    bot.run(os.getenv("DISCORD_TOKEN"))
