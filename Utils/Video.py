import yt_dlp as ytdl
import discord

YTDL_OPTS = {
    "default_search": "ytsearch",
    "format": "bestaudio/best",
    "quiet": True,
    "simulate": True,
    "forceurl": True,
    "extract_flat": "in_playlist",
    "proxy": 'socks5://127.0.0.1:10801'
}


class Video:
    """Class containing information about a particular video."""

    def __init__(self, url_or_search, requested_by):
        """Plays audio from (or searches for) a URL."""
        with ytdl.YoutubeDL(YTDL_OPTS) as ydl:
            video, is_playlist = self._get_info(url_or_search, requested_by)
            self.is_playlist = is_playlist
            if is_playlist:
                self.playlist = video
            else:    
                video_format = video["formats"][5]
                self.stream_url = video_format["url"]
                self.video_url = video["webpage_url"]
                self.title = video["title"]
                self.uploader = video["uploader"] if "uploader" in video else ""
                self.thumbnail = video["thumbnail"] if "thumbnail" in video else None
                self.requested_by = requested_by
            
    def _get_info(self, video_url, requested_by):
        with ytdl.YoutubeDL(YTDL_OPTS) as ydl:
            info = ydl.extract_info(video_url, download=False)
            video = None
            is_list = False
            if "_type" in info and info["_type"] == "playlist":
                result = []
                is_list = True
                for item in info["entries"]:
                    result.append(Video(item["url"], requested_by))
                return result, is_list
            else:
                video = info
            return video, is_list

    def get_embed(self):
        """Makes an embed out of this Video's information."""
        embed = discord.Embed(
            title=self.title, description=self.uploader, url=self.video_url)
        embed.set_footer(
            text=f"Requested by {self.requested_by.name}",
            #icon_url=self.requested_by.avatar_url
        )
        if self.thumbnail:
            embed.set_thumbnail(url=self.thumbnail)
        return embed
