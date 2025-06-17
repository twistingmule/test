import discord
from discord.ext import commands
import yt_dlp
import asyncio
import os
import threading

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
        try:
            await ctx.author.voice.channel.connect()
            await ctx.send("🔊 Joined the voice channel.")
        except discord.ClientException:
            await ctx.send("❗ Already connected.")
        except Exception as e:
            print(f"Join error: {e}")
            await ctx.send("❗ Error joining the channel.")
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
            try:
                vc = await ctx.author.voice.channel.connect()
            except Exception as e:
                print(f"Voice connect error: {e}")
                return await ctx.send("❗ Failed to join the voice channel.")
        else:
            return await ctx.send("❗ You're not in a voice channel.")

    await ctx.send(f"🎵 Searching for: `{search}`...")

    with yt_dlp.YoutubeDL(yt_opts) as ydl:
        try:
            info = ydl.extract_info(search, download=True)
            if 'entries' in info:
                info = info['entries'][0]
            filename = os.path.splitext(ydl.prepare_filename(info))[0] + ".mp3"
        except Exception as e:
            print(f"Download error: {e}")
            return await ctx.send(f"⚠️ Error downloading audio: {e}")

    def after_playing(error):
        if error:
            print(f"Player error: {error}")
        else:
            print("Done playing")
        def delete_file():
            try:
                os.remove(filename)
                print(f"Deleted {filename}")
            except Exception as e:
                print(f"Error deleting file: {e}")
        threading.Timer(2.0, delete_file).start()

    if vc.is_playing():
        vc.stop()

    try:
        vc.play(discord.FFmpegPCMAudio(filename, executable="./ffmpeg"), after=after_playing)
        await ctx.send(f"▶️ Now playing: **{info['title']}**")
    except Exception as e:
        print(f"Playback error: {e}")
        await ctx.send("❗ Failed to play the audio.")

@bot.command()
async def stop(ctx):
    if ctx.voice_client:
        ctx.voice_client.stop()
        await ctx.send("⏹️ Stopped the music.")
    else:
        await ctx.send("❗ I'm not playing anything.")

token = os.getenv("DISCORD_TOKEN")
if not token:
    print("❌ DISCORD_TOKEN environment variable not set.")
else:
    bot.run(token)
