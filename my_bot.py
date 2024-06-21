import discord
from discord.ext import commands
import ssl
import certifi
import os

# 環境変数からトークンを取得
DISCORD_BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN")

# SSLコンテキストの設定
ssl_context = ssl.create_default_context(cafile=certifi.where())

# インテントの設定
intents = discord.Intents.default()
intents.message_content = True

# ボットの設定
bot = commands.Bot(command_prefix='!', intents=intents)

# ボットが起動したときのイベント
@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}')

# コマンドの例
@bot.command()
async def hello(ctx):
    await ctx.send('Hello!')

# ボットを起動する
bot.run(DISCORD_BOT_TOKEN, reconnect=True, ssl=ssl_context)
