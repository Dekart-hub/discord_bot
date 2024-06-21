from ast import alias
import discord
from discord.ext import commands
from discord import app_commands, activity
from youtubesearchpython import VideosSearch
from yt_dlp import YoutubeDL
import asyncio


async def setup(bot):
    await bot.add_cog(music_cog(bot))


class music_cog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

        # all the music related stuff
        self.is_playing = False
        self.is_paused = False

        # 2d array containing [song, channel]
        self.music_queue = []
        self.YDL_OPTIONS = {'format': 'bestaudio/best'}
        self.FFMPEG_OPTIONS = {'options': '-vn'}

        self.vc = None
        self.ytdl = YoutubeDL(self.YDL_OPTIONS)

    @commands.Cog.listener()
    async def on_ready(self):
        print("Music_cog ready")

        # searching the item on youtube

    def search_yt(self, item):
        if item.startswith("https://"):
            title = self.ytdl.extract_info(item, download=False)["title"]
            return {'source': item, 'title': title}
        search = VideosSearch(item, limit=1)
        return {'source': search.result()["result"][0]["link"], 'title': search.result()["result"][0]["title"]}

    async def play_next(self):
        if len(self.music_queue) > 0:
            self.is_playing = True

            # get the first url
            m_url = self.music_queue[0][0]['source']

            # remove the first element as you are currently playing it
            self.music_queue.pop(0)
            loop = asyncio.get_event_loop()
            data = await loop.run_in_executor(None, lambda: self.ytdl.extract_info(m_url, download=False))
            song = data['url']
            self.vc.play(discord.FFmpegPCMAudio(song, executable="ffmpeg.exe", **self.FFMPEG_OPTIONS),
                         after=lambda e: asyncio.run_coroutine_threadsafe(self.play_next(), self.bot.loop))
        else:
            self.is_playing = False

        # infinite loop checking

    async def play_music(self, interaction: discord.Interaction):
        if len(self.music_queue) > 0:
            self.is_playing = True

            m_url = self.music_queue[0][0]['source']
            # try to connect to voice channel if you are not already connected
            if self.vc == None or not self.vc.is_connected():
                self.vc = await self.music_queue[0][1].connect()

                # in case we fail to connect
                if self.vc == None:
                    await interaction.response.send_message("```Could not connect to the voice channel```")
                    return
            else:
                await self.vc.move_to(self.music_queue[0][1])
            # remove the first element as you are currently playing it
            self.music_queue.pop(0)
            loop = asyncio.get_event_loop()
            data = await loop.run_in_executor(None, lambda: self.ytdl.extract_info(m_url, download=False))
            song = data['url']
            self.vc.play(discord.FFmpegPCMAudio(song, executable="ffmpeg.exe", **self.FFMPEG_OPTIONS),
                         after=lambda e: asyncio.run_coroutine_threadsafe(self.play_next(), self.bot.loop))

        else:
            self.is_playing = False

    @app_commands.command(name="play", description="Plays a selected song from youtube")
    @app_commands.describe(querry="Link to or name of a song.")
    async def play(self, interaction: discord.Interaction, querry: str):
        query = " ".join(querry)
        try:
            voice_channel = interaction.user.voice.channel
        except:
            await interaction.response.send_message("```You need to connect to a voice channel first!```")
            return
        if self.is_paused:
            self.vc.resume()
        else:
            song = self.search_yt(query)
            if type(song) == type(True):
                await interaction.response.send_message(
                    "```Could not download the song. Incorrect format try another keyword. This could be due to playlist or a livestream format.```")
            else:
                if self.is_playing:
                    await interaction.response.send_message(f"**#{len(self.music_queue) + 2} -'{song['title']}'** added to the queue")
                else:
                    await interaction.response.send_message(f"**'{song['title']}'** added to the queue")
                self.music_queue.append([song, voice_channel])
                if self.is_playing == False:
                    await self.play_music(interaction)

    @app_commands.command(name="pause", description="Pauses the current song being played")
    async def pause(self, interaction: discord.Interaction):
        if self.is_playing:
            self.is_playing = False
            self.is_paused = True
            self.vc.pause()
            await interaction.response.send_message("```Paused```")
        elif self.is_paused:
            self.is_paused = False
            self.is_playing = True
            self.vc.resume()
            await interaction.response.send_message("```Bot was on pause, but we resumed music for you```")

    @app_commands.command(name="resume", description="Resumes playing with the discord bot")
    async def resume(self, interaction: discord.Interaction):
        if self.is_paused:
            self.is_paused = False
            self.is_playing = True
            self.vc.resume()
            await interaction.response.send_message("```Resumed```")
        else:
            await interaction.response.send_message("```Not on pause```")

    @app_commands.command(name="skip", description="Skips the current song being played")
    async def skip(self, interaction: discord.Interaction):
        if self.vc != None and self.vc:
            self.vc.stop()
            # try to play next in the queue if it exists
            await self.play_music(interaction)
            await interaction.response.send_message("```Skipped```")
        else:
            await interaction.response.send_message("```Not playing```")

    @app_commands.command(name="queue", description="Displays the current songs in queue")
    async def queue(self, interaction: discord.Interaction):
        retval = ""
        for i in range(0, len(self.music_queue)):
            retval += f"#{i + 1} -" + self.music_queue[i][0]['title'] + "\n"

        if retval != "":
            await interaction.response.send_message(f"```queue:\n{retval}```")
        else:
            await interaction.response.send_message("```No music in queue```")

    @app_commands.command(name="clear", description="Stops the music and clears the queue")
    async def clear(self, interaction: discord.Interaction):
        if self.vc != None and self.is_playing:
            self.vc.stop()
        self.music_queue = []
        await interaction.response.send_message("```Music queue cleared```")

    @app_commands.command(name="stop", description="Kick the bot from VC")
    async def dc(self, interaction: discord.Interaction):
        self.is_playing = False
        self.is_paused = False
        await self.vc.disconnect()
        await interaction.response.send_message("```Bye-bye!```")

    @app_commands.command(name="remove", description="Removes last song added to queue")
    async def re(self, interaction: discord.Interaction):
        self.music_queue.pop()
        await interaction.response.send_message("```last song removed```")
