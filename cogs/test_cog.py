import discord
from discord.ext import commands
from discord import app_commands, activity


async def setup(bot):
    await bot.add_cog(test_cog(bot))


class test_cog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        print("test_cog ready")

    @app_commands.command(name="hello", description="Says hello to you ^_^")
    async def hello(self, interaction: discord.Interaction):
        await interaction.response.send_message(f"Hello {interaction.user.mention}")

    @app_commands.command(name="ping", description="Shows bot's latency in ms.")
    async def ping(self, interaction: discord.Interaction):
        bot_latency = round(self.bot.latency * 1000)
        await interaction.response.send_message(f"Pong! {bot_latency} ms.")
