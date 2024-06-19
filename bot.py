import os
import discord
from discord import app_commands
from discord.ext import commands
from dotenv import load_dotenv


def run_bot():
    intents = discord.Intents.default()
    intents.message_content = True
    client = discord.Client(intents=intents)
    tree = app_commands.CommandTree(client)
    client.tree = tree

    @client.event
    async def on_ready():
        print('Logged on')
        await client.tree.sync()

    @client.tree.command(name="echo")
    async def echo(interaction: discord.Interaction):
        await interaction.response.send_message(f"Hello {interaction.user.mention}")

    @client.tree.command(name="sync")
    @commands.is_owner()
    async def sync(interaction: discord.Interaction):
        await tree.sync()

    load_dotenv()
    client.run(os.getenv("DISCORD_TOKEN"))
