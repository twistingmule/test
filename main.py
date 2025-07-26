import discord
from discord.ext import commands
import yt_dlp
import asyncio
import os
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv("DISCORD_BOT_TOKEN")

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

queues = {}

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")

async def play_next(ctx):
    server_id = str(ctx.guild.id)
    if queues[server_id]:
        source = queues[server_id].pop(0)
        ctx.voice_client.play(discord.FFmpegPCMAudio(source), after=lambda e: asyncio.run(play_next(ctx)))

@bot.command()
async def join(ctx):
    if ctx.author.voice:
        await ctx.author.voice.channel.connect()
    else:
        await ctx.send("You must be in a voice channel to summon me.")

@bot.command()
async def play(ctx, *, url):
    server_id = str(ctx.guild.id)
    if server_id not in queues:
        queues[server_id] = []

    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': 'downloads/%(title)s.%(ext)s',
        'noplaylist': True,
        'quiet': True
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        filename = ydl.prepare_filename(info)

    queues[server_id].append(filename)
    if not ctx.voice_client.is_playing():
        await play_next(ctx)

@bot.command()
async def stop(ctx):
    await ctx.voice_client.disconnect()

bot.run(TOKEN)

