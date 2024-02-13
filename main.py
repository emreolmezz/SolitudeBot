import asyncio

import discord
import youtube_dl

import yt_dlp as youtube_dl

from discord.ext import commands

from urllib.parse import urlparse

# Suppress noise about console usage from errors
youtube_dl.utils.bug_reports_message = lambda: ''


ytdl_format_options = {
    'format': 'bestaudio/best',
    'outtmpl': '%(extractor)s-%(id)s-%(title)s.%(ext)s',
    'restrictfilenames': True,
    'noplaylist': True,
    'nocheckcertificate': True,
    'ignoreerrors': False,
    'logtostderr': False,
    'quiet': True,
    'no_warnings': True,
    'default_search': 'auto',
    'source_address': '0.0.0.0',  # bind to ipv4 since ipv6 addresses cause issues sometimes
}

ffmpeg_options = {
    'options': '-vn',
}

ytdl = youtube_dl.YoutubeDL(ytdl_format_options)


class YTDLSource(discord.PCMVolumeTransformer):
    def __init__(self, source, *, data, volume=0.5):
        super().__init__(source, volume)

        self.data = data

        self.title = data.get('title')
        self.url = data.get('url')

    @classmethod
    async def from_title(cls, title, *, loop=None, stream=False):
        #finding youtube songs with title
        loop = loop or asyncio.get_event_loop()
        data = await loop.run_in_executor(None, lambda: ytdl.extract_info(f"ytsearch:{title}", download=not stream))

        if 'entries' in data:
            # take first item from a playlist
            data = data['entries'][0]

        filename = data['url'] if stream else ytdl.prepare_filename(data)
        return cls(discord.FFmpegPCMAudio(filename, **ffmpeg_options), data=data)

    @classmethod
    async def from_url(cls, url, *, loop=None, stream=False):
        #finding youtube songs with url
        loop = loop or asyncio.get_event_loop()
        data = await loop.run_in_executor(None, lambda: ytdl.extract_info(url, download=not stream))

        if 'entries' in data:
            # take first item from a playlist
            data = data['entries'][0]

        filename = data['url'] if stream else ytdl.prepare_filename(data)
        return cls(discord.FFmpegPCMAudio(filename, **ffmpeg_options), data=data)


class Music(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="join", aliases=["j","joining"], help="Join the channel that user currently in")
    async def join(self, ctx):
        #joining the channel that the author user is currently in
        channel = ctx.message.author.voice.channel
        
        if ctx.voice_client is not None:
            return await ctx.voice_client.move_to(channel)

        await channel.connect()


    @commands.command(name="playsong", help="playing song from youtube")
    async def yt(self, ctx, *, query):
        #controlling the query if it is url or not
        parsed_url = urlparse(query)
        if parsed_url.scheme and parsed_url.netloc:
            #play the song with url
            async with ctx.typing():
                player = await YTDLSource.from_url(query)
                ctx.voice_client.play(player, after=lambda e: print(f'Player error: {e}') if e else None)

            await ctx.send(f'Now playing: {player.title}')
        else:
            #play the song with title
            async with ctx.typing():
                player = await YTDLSource.from_title(query)
                ctx.voice_client.play(player, after=lambda e: print(f'Player error: {e}') if e else None)

            await ctx.send(f'Now playing: {player.title}')

    @commands.command()
    async def volume(self, ctx, volume: int):
        #volume changing
        if ctx.voice_client is None:
            return await ctx.send("Not connected to a voice channel.")

        ctx.voice_client.source.volume = volume / 100
        await ctx.send(f"Changed volume to {volume}%")

    @commands.command(name="pause", help="pause the current song")
    async def pause(self, ctx):
        #pausing the song
        if ctx.voice_client.is_playing:
            ctx.voice_client.pause()
            await ctx.send("The audio just paused.")
        else:
            await ctx.send("There is currently no audio playing.")
    
    @commands.command(name="resume", help="resume the current song")
    async def resume(self, ctx):
        #resuming the song
        if ctx.voice_client.is_playing:
            ctx.voice_client.resume()
            await ctx.send("The audio just resumed.")
        else:
            await ctx.send("There is currently no audio playing.")
    
    ## it is not working
    @commands.command(name="helpme", help="help for the commands")
    async def helpme(self, ctx):
        commandsnames = Music.get_commands() 
        for c in commandsnames:
            commandDescription += f"**`!{c.name}`** {c.help}\n"
        commandsEmbed = discord.Embed(
            title="Commands List",
            description=commandDescription,
            colour=self.embedOrange
        )

        await ctx.send(embed=commandsEmbed)
        

    @commands.command(name="disconnect", help="disconnect from channel")
    async def disconnect(self, ctx):
        #disconnect from the channel
        await ctx.voice_client.disconnect()

    @yt.before_invoke
    async def ensure_voice(self, ctx):
        if ctx.voice_client is None:
            if ctx.author.voice:
                await ctx.author.voice.channel.connect()
            else:
                await ctx.send("You are not connected to a voice channel.")
                raise commands.CommandError("Author not connected to a voice channel.")
        elif ctx.voice_client.is_playing():
            ctx.voice_client.stop()


intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(
    command_prefix=commands.when_mentioned_or("/"),
    description='SolitudeMusicBot',
    intents=intents,
)


@bot.event
async def on_ready():
    print(f'Logged in as {bot.user} (ID: {bot.user.id})')
    print('------')



bot.add_cog(Music(bot))
bot.run('YOUR_BOT_TOKEN')