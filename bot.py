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

    @client.tree.command(name="hello", description="Says hello to you ^_^")
    async def hello(interaction: discord.Interaction):
        await interaction.response.send_message(f"Hello {interaction.user.mention}")

    @client.tree.command(name="sync")
    async def sync(interaction: discord.Interaction):
        if interaction.user.id == os.getenv("ADMIN_ID"):
            await client.tree.sync()
            print("Synced!")
        else:
            await interaction.response.send_message(f"ЖОПА")

    @tree.command(name="ping", description="Shows bot's latency in ms.")
    async def ping(interaction: discord.Interaction):
        bot_latency = round(client.latency * 1000)
        await interaction.response.send_message(f"Pong! {bot_latency} ms.")

    load_dotenv()
    client.run(os.getenv("DISCORD_TOKEN"))
