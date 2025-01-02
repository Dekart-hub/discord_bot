import yt_dlp as ytdl
import discord

YTDL_OPTS = {
    "default_search": "ytsearch",
    "format": "bestaudio/best",
    "quiet": True,
    "simulate": True,
    "forceurl": True,
    "extract_flat": "in_playlist",
}


class Video:
    """Class containing information about a particular video."""

    def __init__(self, url_or_search, requested_by):
        """Plays audio from (or searches for) a URL."""
        with ytdl.YoutubeDL(YTDL_OPTS) as ydl:
            video = self._get_info(url_or_search, requested_by)
            self.is_playlist = video["is_playlist"]
            self.requested_by = requested_by
            if self.is_playlist:
                self.playlist_link = url_or_search
                self.playlist = []
                for item in video["entries"]:
                    self.playlist.append({"url": item["url"], "requested_by": requested_by, "title": item["title"]})
            else:    
                video_format = video["formats"][5]
                self.stream_url = video_format["url"]
                self.video_url = video["webpage_url"]
                self.title = video["title"]
                self.uploader = video["uploader"] if "uploader" in video else ""
                self.thumbnail = video["thumbnail"] if "thumbnail" in video else None
                
            
    def _get_info(self, video_url, requested_by):
        with ytdl.YoutubeDL(YTDL_OPTS) as ydl:
            info = ydl.extract_info(video_url, download=False)
            video = info
            video["is_playlist"] = False
            if "_type" in info and info["_type"] == "playlist":
                video["is_playlist"] = True
            return video
        
    def get_playlist(self):
        with ytdl.YoutubeDL(YTDL_OPTS) as ydl:
            info = ydl.extract_info(self.playlist_link, download=False)            
            for item in info["entries"]:
                self.playlist.append(Video(item["url"], self.requested_by))
            return 

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
