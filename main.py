import os

import discord
from dotenv import load_dotenv, dotenv_values


class MyClient(discord.Client):
    async def on_ready(self):
        print('Logged on as {0}!'.format(self.user))


intents = discord.Intents.default()
intents.message_content = True
load_dotenv()

client = MyClient(intents=intents)
client.run(os.getenv("DISCORD_TOKEN"))
