from ast import alias
import discord
from discord.ext import commands
from discord import app_commands, activity
from youtubesearchpython import VideosSearch
from youtube_dl import YoutubeDL
import asyncio


async def setup(bot):
    await bot.add_cog(music_cog(bot))


class music_cog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        await self.bot.change_presence(activity=discord.Game("Online"))

    @app_commands.command(name="slash", description="test slash command")
    async def ping(self, interaction: discord.Interaction):
        bot_latency = round(self.bot.latency * 1000)
        await interaction.response.send_message(f"Pong! {bot_latency} ms.")
