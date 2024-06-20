import os
import discord
from discord import app_commands
from discord.ext import commands
from dotenv import load_dotenv
from music_cog import music_cog


def run_bot():
    intents = discord.Intents.default()
    intents.message_content = True
    bot = commands.Bot(command_prefix='!', intents=intents)

    @bot.event
    async def on_ready():
        print('Logged on')

    @bot.tree.command(name="hello", description="Says hello to you ^_^")
    async def hello(interaction: discord.Interaction):
        await interaction.response.send_message(f"Hello {interaction.user.mention}")

    @bot.command(name="sync")
    async def sync(ctx):
        if ctx.author.id == int(os.getenv("ADMIN_ID")):
            await bot.tree.sync()
            print("Synced!")
        else:
            await ctx.send("ZHOPA")

    @bot.tree.command(name="ping", description="Shows bot's latency in ms.")
    async def ping(interaction: discord.Interaction):
        bot_latency = round(bot.latency * 1000)
        await interaction.response.send_message(f"Pong! {bot_latency} ms.")

    load_dotenv()
    bot.run(os.getenv("DISCORD_TOKEN"))
