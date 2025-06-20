import os
import threading
import discord
from discord.ext import commands
from openai import OpenAI
from flask import Flask

client = OpenAI(
    api_key=os.getenv("OPENROUTER_API_KEY"),
    base_url="https://openrouter.ai/api/v1"
)

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

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
        "**Here are my available commands:**\n"
        "\n"
        "• `!ping` - Check if the bot is responsive\n"
        "• `!ask <question>` - Ask me anything using AI\n"
        "• `!help` - Show this help message"
    )
    await ctx.send(help_text)

app = Flask(__name__)

@app.route("/")
def home():
    return "Discord Bot is running!"

def run_bot():
    bot.run(os.getenv("DISCORD_TOKEN"))

if __name__ == "__main__":
    threading.Thread(target=run_bot).start()
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
