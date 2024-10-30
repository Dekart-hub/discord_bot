import discord
from discord.ext import commands
from discord import app_commands
import yt_dlp as youtube_dl
import asyncio
import logging
import math
import config
from Utils.Video import Video


async def setup(bot):
    await bot.add_cog(music_cog(bot))


# FFMPEG_BEFORE_OPTS = '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5'
FFMPEG_OPTS = {'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5', 'options': '-vn'}


async def audio_playing(ctx):
    """Checks that audio is currently playing before continuing."""
    client = ctx.guild.voice_client
    if client and client.channel and client.source:
        return True
    else:
        raise commands.CommandError("Not currently playing any audio.")


async def in_voice_channel(interaction: discord.Interaction):
    """Checks that the command sender is in the same voice channel as the bot."""
    voice = interaction.user.voice
    bot_voice = interaction.guild.voice_client
    if voice and bot_voice and voice.channel and bot_voice.channel and voice.channel == bot_voice.channel:
        return True
    else:
        raise app_commands.AppCommandError(
            "You need to be in the channel to do that.")


async def is_audio_requester(ctx):
    """Checks that the command sender is the song requester."""
    music = ctx.bot.get_cog("Music")
    state = music.get_state(ctx.guild)
    permissions = ctx.channel.permissions_for(ctx.author)
    if permissions.administrator or state.is_requester(ctx.author):
        return True
    else:
        raise commands.CommandError(
            "You need to be the song requester to do that.")


class music_cog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.config = config.load_config()  # retrieve module name, find config entry
        self.states = {}
        self.bot.add_listener(self.on_reaction_add, "on_reaction_add")

    @commands.Cog.listener()
    async def on_ready(self):
        print("music_cog ready")

    def get_state(self, guild):
        """Gets the state for `guild`, creating it if it does not exist."""
        if guild.id in self.states:
            return self.states[guild.id]
        else:
            self.states[guild.id] = GuildState()
            return self.states[guild.id]

    @app_commands.command(name="leave", description="Leaves channel.")
    @app_commands.guild_only()
    async def leave(self, interection: discord.Interaction):
        """Leaves the voice channel, if currently in one."""
        client = interection.guild.voice_client
        state = self.get_state(interection.guild)
        if client and client.channel:
            await client.disconnect()
            state.playlist = []
            state.now_playing = None
            await interection.response.send_message("Left.")
        else:
            await interection.response.send_message("Not in a voice channel.")

    @app_commands.command(name="pause", description="Pauses/Resumes playing.")
    @app_commands.guild_only()
    @app_commands.check(audio_playing)
    @app_commands.check(in_voice_channel)
    async def pause(self, interection: discord.Interaction):
        """Pauses any currently playing audio."""
        client = interection.guild.voice_client
        self._pause_audio(client)
        await interection.response.send_message("Paused")

    def _pause_audio(self, client):
        if client.is_paused():
            client.resume()
        else:
            client.pause()

    # @commands.command(aliases=["vol", "v"])
    # @commands.guild_only()
    # @commands.check(audio_playing)
    # @commands.check(in_voice_channel)
    # @commands.check(is_audio_requester)
    # async def volume(self, ctx, volume: int):
    #     """Change the volume of currently playing audio (values 0-250)."""
    #     state = self.get_state(ctx.guild)
    #
    #     # make sure volume is nonnegative
    #     if volume < 0:
    #         volume = 0
    #
    #     max_vol = self.config["max_volume"]
    #     if max_vol > -1:  # check if max volume is set
    #         # clamp volume to [0, max_vol]
    #         if volume > max_vol:
    #             volume = max_vol
    #
    #     client = ctx.guild.voice_client
    #
    #     state.volume = float(volume) / 100.0
    #     client.source.volume = state.volume  # update the AudioSource's volume to match

    @app_commands.command(name="skip", description="Skips current song.")
    @app_commands.guild_only()
    @app_commands.check(audio_playing)
    @app_commands.check(in_voice_channel)
    async def skip(self, interaction: discord.Interaction):
        """Skips the currently playing song, or votes to skip it."""
        state = self.get_state(interaction.guild)
        client = interaction.guild.voice_client
        client.stop()
        await interaction.response.send_message("Skipped!")

    def _vote_skip(self, channel, member):
        """Register a vote for `member` to skip the song playing."""
        logging.info(f"{member.name} votes to skip")
        state = self.get_state(channel.guild)
        state.skip_votes.add(member)
        users_in_channel = len([
            member for member in channel.members if not member.bot
        ])  # don't count bots
        if (float(len(state.skip_votes)) /
            users_in_channel) >= self.config["vote_skip_ratio"]:
            # enough members have voted to skip, so skip the song
            logging.info(f"Enough votes, skipping...")
            channel.guild.voice_client.stop()

    def _play_song(self, client, state, song):
        state.now_playing = song
        state.skip_votes = set()  # clear skip votes
        # source = discord.PCMVolumeTransformer(
        #     discord.FFmpegPCMAudio(song.stream_url, before_options=FFMPEG_BEFORE_OPTS), volume=state.volume)
        source = discord.FFmpegOpusAudio(song.stream_url, **FFMPEG_OPTS)

        def after_playing(err):
            if len(state.playlist) > 0:
                next_song = state.playlist.pop(0)
                self._play_song(client, state, next_song)
            else:
                asyncio.run_coroutine_threadsafe(client.disconnect(),
                                                 self.bot.loop)

        client.play(source, after=after_playing)

    @app_commands.command(name="nowplaying", description="Shows current playing track.")
    @app_commands.guild_only()
    @app_commands.check(audio_playing)
    async def nowplaying(self, interaction: discord.Interaction):
        """Displays information about the current song."""
        state = self.get_state(interaction.guild)
        await interaction.response.send_message("", embed=state.now_playing.get_embed())
        # await self._add_reaction_controls(message)

    @app_commands.command(name="queue", description="Shows queue.")
    @app_commands.guild_only()
    @app_commands.check(audio_playing)
    async def queue(self, interaction: discord.Interaction):
        """Display the current play queue."""
        state = self.get_state(interaction.guild)
        await interaction.response.send_message(self._queue_text(state.playlist))

    def _queue_text(self, queue):
        """Returns a block of text describing a given song queue."""
        if len(queue) > 0:
            message = [f"{len(queue)} songs in queue:"]
            message += [
                f"  {index + 1}. **{song.title}** (requested by **{song.requested_by.name}**)"
                for (index, song) in enumerate(queue)
            ]  # add individual songs
            return "\n".join(message)
        else:
            return "The play queue is empty."

    @app_commands.command(name="clear", description="Clears queue.")
    @app_commands.guild_only()
    @app_commands.check(audio_playing)
    async def clearqueue(self, interaction: discord.Interaction):
        """Clears the play queue without leaving the channel."""
        state = self.get_state(interaction.guild)
        state.playlist = []
        await interaction.response.send_message("Cleared")

    @app_commands.command(name="play", description="Plays audio from <url> or by name.")
    @app_commands.describe(url="Link or name of a song.")
    @app_commands.guild_only()
    async def play(self, interaction: discord.Interaction, url: str):
        """Plays audio hosted at <url> (or performs a search for <url> and plays the first result)."""

        client = interaction.guild.voice_client
        state = self.get_state(interaction.guild)  # get the guild's state

        await interaction.response.send_message(f"Searching for {url}")
        if client and client.channel:
            try:
                video = Video(url, interaction.user)
            except youtube_dl.DownloadError as e:
                logging.warning(f"Error downloading video: {e}")
                await interaction.followup.send(
                    "There was an error downloading your video, sorry.")
                return
            if video.is_playlist:
                state.playlist.extend(video.playlist)
                await interaction.followup.send("Added to queue.", embed=video.playlist[0].get_embed())
            else:
                state.playlist.append(video)
                await interaction.followup.send("Added to queue.", embed=video.get_embed())
        else:
            if interaction.user.voice is not None and interaction.user.voice.channel is not None:
                channel = interaction.user.voice.channel
                try:
                    video = Video(url, interaction.user)
                except youtube_dl.DownloadError as e:
                    await interaction.followup.send(
                        "There was an error downloading your video, sorry.")
                    return
                client = await channel.connect()
                if video.is_playlist:
                    self._play_song(client, state, video.playlist[0])
                    state.playlist.extend(video.playlist[1:])
                    await interaction.followup.send("", embed=video.playlist[0].get_embed())
                    logging.info(f"Now playing '{video.playlist[0].title}'")
                else:
                    self._play_song(client, state, video)
                    await interaction.followup.send("", embed=video.get_embed())
                    logging.info(f"Now playing '{video.title}'")
            else:
                raise commands.CommandError(
                    "You need to be in a voice channel to do that.")

    async def on_reaction_add(self, reaction, user):
        """Respods to reactions added to the bot's messages, allowing reactions to control playback."""
        message = reaction.message
        if user != self.bot.user and message.author == self.bot.user:
            await message.remove_reaction(reaction, user)
            if message.guild and message.guild.voice_client:
                user_in_channel = user.voice and user.voice.channel and user.voice.channel == message.guild.voice_client.channel
                permissions = message.channel.permissions_for(user)
                guild = message.guild
                state = self.get_state(guild)
                if permissions.administrator or (
                        user_in_channel and state.is_requester(user)):
                    client = message.guild.voice_client
                    if reaction.emoji == "⏯":
                        # pause audio
                        self._pause_audio(client)
                    elif reaction.emoji == "⏭":
                        # skip audio
                        client.stop()
                    elif reaction.emoji == "⏮":
                        state.playlist.insert(
                            0, state.now_playing
                        )  # insert current song at beginning of playlist
                        client.stop()  # skip ahead
                elif reaction.emoji == "⏭" and self.config[
                    "vote_skip"] and user_in_channel and message.guild.voice_client and message.guild.voice_client.channel:
                    # ensure that skip was pressed, that vote skipping is
                    # enabled, the user is in the channel, and that the bot is
                    # in a voice channel
                    voice_channel = message.guild.voice_client.channel
                    self._vote_skip(voice_channel, user)
                    # announce vote
                    channel = message.channel
                    users_in_channel = len([
                        member for member in voice_channel.members
                        if not member.bot
                    ])  # don't count bots
                    required_votes = math.ceil(
                        self.config["vote_skip_ratio"] * users_in_channel)
                    await channel.send(
                        f"{user.mention} voted to skip ({len(state.skip_votes)}/{required_votes} votes)"
                    )

    async def _add_reaction_controls(self, message):
        """Adds a 'control-panel' of reactions to a message that can be used to control the bot."""
        CONTROLS = ["⏮", "⏯", "⏭"]
        for control in CONTROLS:
            await message.add_reaction(control)


class GuildState:
    """Helper class managing per-guild state."""

    def __init__(self):
        self.volume = 1.0
        self.playlist = []
        self.skip_votes = set()
        self.now_playing = None

    def is_requester(self, user):
        return self.now_playing.requested_by == user
