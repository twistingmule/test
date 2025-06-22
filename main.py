import os
import threading
import discord
from discord.ext import commands
from openai import OpenAI
from flask import Flask

# === Environment Variables ===
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

if not DISCORD_TOKEN or not OPENROUTER_API_KEY:
    raise ValueError("Missing DISCORD_TOKEN or OPENROUTER_API_KEY environment variables.")

# === OpenAI / OpenRouter Client Setup ===
client = OpenAI(
    api_key=OPENROUTER_API_KEY,
    base_url="https://openrouter.ai/api/v1"
)

# === Discord Bot Setup ===
intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)
bot.remove_command("help")  # Remove default help command to avoid conflicts

@bot.event
async def on_ready():
    print(f"🤖 Bot is online as {bot.user}")

@bot.command()
async def ping(ctx):
    await ctx.send("Pong!")

@bot.command()
async def ask(ctx, *, question=None):
    if not question:
        await ctx.send("❗ You need to ask a question, like:\n`!ask What is the meaning of life?`")
        return

    async with ctx.channel.typing():
        try:
            response = client.chat.completions.create(
                model="deepseek/deepseek-r1-0528-qwen3-8b:free",
                messages=[{"role": "user", "content": question}]
            )
            answer = response.choices[0].message.content.strip()
            await ctx.send(answer[:2000])
        except Exception as e:
            await ctx.send(f"⚠️ Error: {str(e)}")

@bot.command(name="help")
async def custom_help(ctx):
    help_text = (
        "**Here are my available commands:**\n\n"
        "• `!ping` - Check if the bot is responsive\n"
        "• `!ask <question>` - Ask me anything using AI\n"
        "• `!help` - Show this help message"
    )
    await ctx.send(help_text)

# === Flask Server for Uptime Monitoring or Hosting ===
app = Flask(__name__)

@app.route("/")
def home():
    return "Discord Bot is running!"

def run_bot():
    try:
        bot.run(DISCORD_TOKEN)
    except Exception as e:
        print(f"❌ Bot failed to start: {e}")

# === Entry Point ===
if __name__ == "__main__":
    threading.Thread(target=run_bot).start()
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
