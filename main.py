import discord
from discord.ext import commands
import yt_dlp
import asyncio
import os

# Ensure the downloads directory exists
os.makedirs("downloads", exist_ok=True)

# Set up Discord bot intents
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# YouTube download options
yt_opts = {
    'format': 'bestaudio/best',
    'quiet': True,
    'noplaylist': True,
    'default_search': 'ytsearch',
    'outtmpl': 'downloads/%(title)s.%(ext)s',
    'postprocessors': [{
        'key': 'FFmpegExtractAudio',
        'preferredcodec': 'mp3',
        'preferredquality': '192',
    }],
}

@bot.event
async def on_ready():
    print(f"🎶 Music Bot online as {bot.user}")

@bot.command()
async def join(ctx):
    if ctx.author.voice:
        await ctx.author.voice.channel.connect()
        await ctx.send("🔊 Joined the voice channel.")
    else:
        await ctx.send("❗ You're not in a voice channel.")

@bot.command()
async def leave(ctx):
    if ctx.voice_client:
        await ctx.voice_client.disconnect()
        await ctx.send("👋 Left the voice channel.")
    else:
        await ctx.send("❗ I'm not in a voice channel.")

@bot.command()
async def play(ctx, *, search: str):
    vc = ctx.voice_client
    if not vc:
        if ctx.author.voice:
            vc = await ctx.author.voice.channel.connect()
        else:
            return await ctx.send("❗ You're not in a voice channel.")

    await ctx.send(f"🎵 Searching for: `{search}`...")

    with yt_dlp.YoutubeDL(yt_opts) as ydl:
        try:
            info = ydl.extract_info(search, download=True)
            if 'entries' in info:  # Handle search result lists
                info = info['entries'][0]
            filename = ydl.prepare_filename(info).replace(".webm", ".mp3").replace(".m4a", ".mp3")
        except Exception as e:
            return await ctx.send(f"⚠️ Error: {e}")

    def after_playing(error):
        if error:
            print(f"Player error: {error}")
        else:
            print("Done playing")
        try:
            os.remove(filename)
        except Exception as e:
            print(f"Error deleting file: {e}")

    vc.stop()
    vc.play(discord.FFmpegPCMAudio(filename), after=after_playing)
    await ctx.send(f"▶️ Now playing: **{info['title']}**")

@bot.command()
async def stop(ctx):
    if ctx.voice_client:
        ctx.voice_client.stop()
        await ctx.send("⏹️ Stopped the music.")

# Run the bot with your token from environment variable
bot.run(os.getenv("DISCORD_TOKEN"))
