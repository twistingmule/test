import os
import asyncio
from typing import Optional
import discord
from discord.ext import commands
from dotenv import load_dotenv
import yt_dlp

# ---------- Config ----------
load_dotenv()
TOKEN = os.getenv("DISCORD_BOT_TOKEN")
PREFIX = os.getenv("PREFIX", "!")

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix=PREFIX, intents=intents)

YTDL_OPTS = {
    "format": "bestaudio/best",
    "noplaylist": True,
    "quiet": True,
    "default_search": "ytsearch",
    "extract_flat": False,
    "source_address": "0.0.0.0",
}
FFMPEG_OPTS = {
    "before_options": "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5",
    "options": "-vn",
}

class GuildPlayer:
    def __init__(self, guild_id: int):
        self.guild_id = guild_id
        self.queue: asyncio.Queue[dict] = asyncio.Queue()
        self.play_next = asyncio.Event()
        self.current: Optional[dict] = None
        self.loop_task: Optional[asyncio.Task] = None

    async def ensure_loop(self, ctx: commands.Context):
        if self.loop_task is None or self.loop_task.done():
            self.loop_task = asyncio.create_task(self.player_loop(ctx))

    async def player_loop(self, ctx: commands.Context):
        while True:
            self.play_next.clear()
            self.current = await self.queue.get()
            url = self.current["webpage_url"]
            title = self.current.get("title", "Unknown Title")

            if not ctx.voice_client:
                # Try to rejoin author channel if disconnected
                if ctx.author.voice and ctx.author.voice.channel:
                    await ctx.author.voice.channel.connect()
                else:
                    await ctx.send("I'm not in a voice channel and can't find yours. Use `!join` first.")
                    continue

            try:
                # Get a fresh audio URL (some expire), use direct URL if present
                if "url" in self.current and self.current.get("is_live") is False:
                    audio_url = self.current["url"]
                else:
                    with yt_dlp.YoutubeDL(YTDL_OPTS) as ydl:
                        info = ydl.extract_info(url, download=False)
                        audio_url = info["url"]

                source = discord.FFmpegPCMAudio(audio_url, **FFMPEG_OPTS)
                vc = ctx.voice_client
                if vc.is_playing():
                    vc.stop()

                def after_play(err):
                    if err:
                        print("Player error:", err)
                    self.play_next.set()

                vc.play(source, after=after_play)
                await ctx.send(f"▶️ Now playing: **{title}**")
                await self.play_next.wait()
            except Exception as e:
                await ctx.send(f"❌ Error playing track: `{e}`")

players: dict[int, GuildPlayer] = {}

def get_player(guild_id: int) -> GuildPlayer:
    gp = players.get(guild_id)
    if not gp:
        gp = GuildPlayer(guild_id)
        players[guild_id] = gp
    return gp

def ytdlp_search(query: str) -> dict:
    """Return the best match info dict for a query or URL."""
    with yt_dlp.YoutubeDL(YTDL_OPTS) as ydl:
        info = ydl.extract_info(query, download=False)
        # If the query is "ytsearch: ..." we might get a 'entries' list
        if "entries" in info and info["entries"]:
            return info["entries"][0]
        return info

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user} (ID: {bot.user.id})")
    print("------")

# ---------- Voice Commands ----------

@bot.command(help="Join your current voice channel.")
async def join(ctx: commands.Context):
    if ctx.author.voice and ctx.author.voice.channel:
        channel = ctx.author.voice.channel
        if ctx.voice_client:
            if ctx.voice_client.channel != channel:
                await ctx.voice_client.move_to(channel)
        else:
            await channel.connect()
        await ctx.send(f"✅ Joined **{channel}**")
    else:
        await ctx.send("You need to be in a voice channel first.")

@bot.command(help="Leave the voice channel.")
async def leave(ctx: commands.Context):
    if ctx.voice_client:
        await ctx.voice_client.disconnect()
        await ctx.send("👋 Left the voice channel.")
    else:
        await ctx.send("I'm not connected to a voice channel.")

# ---------- Playback Commands ----------

@bot.command(aliases=["p"], help="Play a song from a URL or search. Example: !play never gonna give you up")
async def play(ctx: commands.Context, *, query: str):
    if not ctx.voice_client:
        await join(ctx)
        if not ctx.voice_client:
            return

    player = get_player(ctx.guild.id)
    try:
        info = ytdlp_search(query)
        await player.queue.put(info)
        await ctx.send(f"➕ Queued: **{info.get('title','Unknown Title')}**")
        await player.ensure_loop(ctx)
    except Exception as e:
        await ctx.send(f"❌ Couldn't add to queue: `{e}`")

@bot.command(help="Show the current track.")
async def now(ctx: commands.Context):
    player = get_player(ctx.guild.id)
    if player.current:
        await ctx.send(f"🎵 Now: **{player.current.get('title','Unknown Title')}**")
    else:
        await ctx.send("Nothing is playing.")

@bot.command(help="Skip the current track.")
async def skip(ctx: commands.Context):
    if ctx.voice_client and ctx.voice_client.is_playing():
        ctx.voice_client.stop()
        await ctx.send("⏭️ Skipped.")
    else:
        await ctx.send("Nothing to skip.")

@bot.command(help="Pause playback.")
async def pause(ctx: commands.Context):
    if ctx.voice_client and ctx.voice_client.is_playing():
        ctx.voice_client.pause()
        await ctx.send("⏸️ Paused.")
    else:
        await ctx.send("Nothing is playing.")

@bot.command(help="Resume playback.")
async def resume(ctx: commands.Context):
    if ctx.voice_client and ctx.voice_client.is_paused():
        ctx.voice_client.resume()
        await ctx.send("▶️ Resumed.")
    else:
        await ctx.send("Nothing is paused.")

@bot.command(help="Stop and clear the queue.")
async def stop(ctx: commands.Context):
    player = get_player(ctx.guild.id)
    while not player.queue.empty():
        try:
            player.queue.get_nowait()
            player.queue.task_done()
        except asyncio.QueueEmpty:
            break
    if ctx.voice_client and ctx.voice_client.is_playing():
        ctx.voice_client.stop()
    await ctx.send("⏹️ Stopped and cleared the queue.")

@bot.command(help="Show how many items are queued.")
async def queue(ctx: commands.Context):
    player = get_player(ctx.guild.id)
    qsize = player.queue.qsize()
    if qsize == 0:
        await ctx.send("The queue is empty.")
    else:
        await ctx.send(f"📜 Items in queue: **{qsize}**")

# ---------- Run ----------
if __name__ == "__main__":
    if not TOKEN:
        raise RuntimeError("DISCORD_BOT_TOKEN not set. Put it in a .env file or environment variable.")
    bot.run(TOKEN)
