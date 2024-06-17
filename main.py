import os

import discord
from dotenv import load_dotenv, dotenv_values


class MyClient(discord.Client):
    async def on_ready(self):
        print('Logged on as {0}!'.format(self.user))


load_dotenv()
client = MyClient()
client.run(os.getenv("DISCORD_TOKEN"))
