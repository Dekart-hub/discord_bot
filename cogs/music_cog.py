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


async def audio_playing(interaction: discord.Interaction):
    """Checks that audio is currently playing before continuing."""
    client = interaction.guild.voice_client
    if client and client.channel and client.source:
        return True
    else:
        raise app_commands.AppCommandError("Not currently playing any audio.")


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
        
    async def start_disconnect_timer(self, guild, client):
        """Запускает таймер отключения"""
        state = self.get_state(guild)
        
        # Отменяем существующий таймер, если он есть
        if state.disconnect_timer and not state.disconnect_timer.done():
            state.disconnect_timer.cancel()
            
        # Создаем новый таймер
        state.disconnect_timer = asyncio.create_task(self.disconnect_after_timeout(guild, client))

    async def disconnect_after_timeout(self, guild, client):
        """Отключается после 5 минут бездействия"""
        try:
            await asyncio.sleep(300)  # 5 минут = 300 секунд
            if client and client.is_connected():
                await client.disconnect()
                state = self.get_state(guild)
                state.playlist = []
                state.now_playing = None
                state.disconnect_timer = None
                logging.info(f"Disconnected from {guild.name} due to inactivity")
        except asyncio.CancelledError:
            # Таймер был отменен
            logging.info(f"Disconnect timer was cancelled for {guild.name}")
            pass
        except Exception as e:
            logging.error(f"Error in disconnect timer for {guild.name}: {e}")

    async def reset_disconnect_timer(self, guild, client):
        """Сбрасывает таймер отключения"""
        await self.start_disconnect_timer(guild, client)

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
        await self.reset_disconnect_timer(interection.guild, client)
        if client.is_paused():
            client.resume()
            await interection.response.send_message("Resumed")
        else:
            client.pause()
            await interection.response.send_message("Paused")

    @app_commands.command(name="volume", description="Изменить громкость воспроизведения (0-250)")
    @app_commands.describe(volume="Значение громкости от 0 до 250")
    @app_commands.guild_only()
    @app_commands.check(audio_playing)
    @app_commands.check(in_voice_channel)
    async def volume(self, interaction: discord.Interaction, volume: int):
        """Изменяет громкость воспроизведения (значения 0-250)."""
        state = self.get_state(interaction.guild)
        client = interaction.guild.voice_client

        # Проверяем, что громкость неотрицательная
        if volume < 0:
            volume = 0

        # Проверяем максимальную громкость из конфига
        max_vol = self.config["max_volume"]
        if max_vol > -1:  # проверяем, установлен ли максимум
            if volume > max_vol:
                volume = max_vol

        # Преобразуем громкость в диапазон 0-2.0
        state.volume = float(volume) / 100.0

        # Создаем новый источник аудио с новой громкостью
        current_source = client.source
        if current_source:
            audio = discord.FFmpegOpusAudio(
                state.now_playing.stream_url,
                **FFMPEG_OPTS,
                options=f'{FFMPEG_OPTS["options"]} -filter:a volume={state.volume}'
            )

            # Останавливаем текущее воспроизведение
            client.stop()

            # Начинаем воспроизведение с новой громкостью
            def after_playing(err):
                if err:
                    logging.error(f"Error in playback after volume change: {err}")

            client.play(audio, after=after_playing)

            await interaction.response.send_message(f"Громкость изменена на {volume}%")
        else:
            await interaction.response.send_message("В данный момент ничего не воспроизводится.")

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

    async def _play_song(self, client, state, song):
        state.now_playing = song
        source = discord.FFmpegOpusAudio(song.stream_url, **FFMPEG_OPTS)
        await self.reset_disconnect_timer(client.guild, client)

        def after_playing(err):
            if err:
                logging.error(f"Error in playback: {err}")
        
            async def play_next():
                if len(state.playlist) > 0:
                    next_song = state.playlist.pop(0)
                    try:
                        video = Video(next_song["url"], next_song["requested_by"])
                        await self._play_song(client, state, video)
                    except youtube_dl.DownloadError as e:
                        logging.error(f"Error downloading next video: {e}")
                        if len(state.playlist) > 0:
                            await play_next()
                else:
                    await self.start_disconnect_timer(client.guild, client)

            coro = play_next()
            fut = asyncio.run_coroutine_threadsafe(coro, self.bot.loop)
            try:
                fut.result()
            except Exception as e:
                logging.error(f"Error in play_next: {e}")

        client.play(source, after=after_playing)

    @app_commands.command(name="nowplaying", description="Shows current playing track.")
    @app_commands.guild_only()
    @app_commands.check(audio_playing)
    async def nowplaying(self, interaction: discord.Interaction):
        """Displays information about the current song."""
        state = self.get_state(interaction.guild)
        if state.now_playing:
            await interaction.response.send_message("", embed=state.now_playing.get_embed())
        else:
            await interaction.response.send_message("Not currently playing any audio")

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
                f"  {index + 1}. **{song['title']}** (requested by **{song['requested_by']}**)"
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
            await self.reset_disconnect_timer(interaction.guild, client)
            try:
                video = Video(url, interaction.user)
            except youtube_dl.DownloadError as e:
                logging.warning(f"Error downloading video: {e}")
                await interaction.followup.send(
                    "There was an error downloading your video, sorry.")
                return
            if video.is_playlist:
                state.playlist.extend(video.playlist)
                title = video.playlsit[0]["title"]
                await interaction.followup.send(f"Added to queue {title} and {len(video.playlist)} more tracks")
            else:
                #state.playlist.append(video)
                state.playlist.append(url)
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
                    state.playlist.extend(video.playlist[1:])
                    try:
                        video = Video(video.playlist[0]["url"], interaction.user)
                    except youtube_dl.DownloadError as e:
                        await interaction.followup.send(
                            "There was an error downloading your video, sorry.")
                        return
                    await self._play_song(client, state, video)
                    await interaction.followup.send("", embed=video.get_embed())
                    logging.info(f"Now playing '{video.title}'")
                else:
                    await self._play_song(client, state, video)
                    await interaction.followup.send("", embed=video.get_embed())
                    logging.info(f"Now playing '{video.title}'")
            else:
                raise commands.CommandError(
                    "You need to be in a voice channel to do that.")

    @app_commands.command(name="goto", description="Перейти к указанной позиции в очереди")
    @app_commands.describe(position="Номер позиции в очереди (1-N)")
    @app_commands.guild_only()
    @app_commands.check(audio_playing)
    @app_commands.check(in_voice_channel)
    async def goto(self, interaction: discord.Interaction, position: int):
        """Переходит к воспроизведению трека с указанной позиции в очереди."""
        state = self.get_state(interaction.guild)
        client = interaction.guild.voice_client

        # Проверяем корректность введенной позиции
        if position < 1 or position > len(state.playlist):
            await interaction.response.send_message(
                f"Некорректная позиция. Введите число от 1 до {len(state.playlist)}")
            return

        # Получаем треки до указанной позиции
        removed_tracks = state.playlist[:position-1]

        # Обновляем плейлист, начиная с указанной позиции
        state.playlist = state.playlist[position-1:]

        # Останавливаем текущее воспроизведение, что автоматически запустит следующий трек
        client.stop()


class GuildState:
    """Helper class managing per-guild state."""
    
    def __init__(self):
        self.volume = 1.0
        self.playlist = []
        self.skip_votes = set()
        self.now_playing = None
        self.disconnect_timer = None

    def is_requester(self, user):
        return self.now_playing.requested_by == user
