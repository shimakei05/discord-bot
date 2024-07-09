import discord
from discord import app_commands
from discord.ext import commands
from collections import defaultdict
import datetime
import json
import os
import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from pytz import timezone

logging.basicConfig(level=logging.INFO)

# 環境変数からトークンを取得
DISCORD_BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN")

# データファイルのパス
DATA_FILE = "user_data.json"

# 管理者のユーザーID
ADMIN_USER_IDS = {720219524531748884}  # ここに管理者のユーザーIDを追加

# インテントの設定
intents = discord.Intents.default()
intents.messages = True
intents.message_content = True  # メッセージ内容のインテントを有効にする
intents.guilds = True
intents.reactions = True  # リアクションのインテントを有効にする

bot = commands.Bot(command_prefix="!", intents=intents)

# ポイントとデータを保存する辞書
user_points = defaultdict(int)
last_login_date = defaultdict(lambda: None)  # ユーザーの最終ログイン日を保存する辞書
login_streaks = defaultdict(int)  # 連続ログイン日数を保存する辞書
monthly_message_count = defaultdict(int)  # 1ヶ月のメッセージ数を保存する辞書

current_date = datetime.datetime.now(timezone("Asia/Tokyo")).date()

def save_data():
    """ポイントとデータを保存"""
    data = {
        "user_points": dict(user_points),
        "last_login_date": {str(k): str(v) for k, v in last_login_date.items()},
        "login_streaks": dict(login_streaks),
        "monthly_message_count": dict(monthly_message_count)
    }
    with open(DATA_FILE, "w") as f:
        json.dump(data, f)
    logging.info("データが保存されました: %s", data)

def load_data():
    """ポイントとデータを読み込む"""
    global user_points, last_login_date, login_streaks, monthly_message_count
    try:
        with open(DATA_FILE, "r") as f:
            data = json.load(f)
            user_points.update(data.get("user_points", {}))
            last_login_date.update({int(k): datetime.datetime.fromisoformat(v).date() for k, v in data.get("last_login_date", {}).items()})
            login_streaks.update(data.get("login_streaks", {}))
            monthly_message_count.update(data.get("monthly_message_count", {}))
        logging.info("データが読み込まれました: %s", data)
    except FileNotFoundError:
        logging.info("データファイルが見つかりません。新しいファイルを作成します。")
    except json.JSONDecodeError:
        logging.error("データファイルの読み込みに失敗しました。JSON形式に問題があります。")

@bot.event
async def on_ready():
    logging.info(f'Logged in as {bot.user}')
    try:
        synced = await bot.tree.sync()
        logging.info(f'Synced {len(synced)} command(s)')
    except Exception as e:
        logging.error(f'Failed to sync commands: {e}')
    load_data()  # データの読み込み
    logging.info(f'ポイントデータ: {user_points}')  # 追加: ポイントデータの確認
    scheduler.start()  # スケジューラの開始

@bot.event
async def on_disconnect():
    logging.warning('Bot has been disconnected')

@bot.event
async def on_resumed():
    logging.info('Bot has resumed connection')

def check_and_give_login_bonus(user_id, today):
    last_login = last_login_date[user_id]
    bonus_message = ""
    logging.info(f'チェック中: user_id={user_id}, last_login={last_login}, today={today}')
    if last_login is None or last_login != today:
        user_points[user_id] += 50
        bonus_message = "ログインボーナスとして 50 🪙 ポイントを獲得しました！"
        if last_login is None or (today - last_login).days > 1:
            login_streaks[user_id] = 1
        else:
            login_streaks[user_id] += 1

        streak_days = login_streaks[user_id]
        if streak_days == 3:
            user_points[user_id] += 50
            bonus_message += " さらに、3日連続のログインボーナスとして追加で50ポイントを獲得しました！"
        elif streak_days == 5:
            user_points[user_id] += 100
            bonus_message += " さらに、5日連続のログインボーナスとして追加で100ポイントを獲得しました！"
        elif streak_days == 10:
            user_points[user_id] += 200
            bonus_message += " さらに、10日連続のログインボーナスとして追加で200ポイントを獲得しました！"
            login_streaks[user_id] = 0

        last_login_date[user_id] = today
        logging.info(f'ログインボーナス付与: user_id={user_id}, streak_days={streak_days}, points={user_points[user_id]}')
        return bonus_message
    logging.info(f'ログインボーナスなし: user_id={user_id}, last_login={last_login}, today={today}')
    return bonus_message

def reset_daily_tasks():
    global current_date
    today = datetime.datetime.now(timezone("Asia/Tokyo")).date()
    logging.info(f"タスク実行 - 現在の日付: {today}, 記録された日付: {current_date}")  # 日付変更確認用のログ

    # 日付が変更された場合
    if today != current_date:
        logging.info(f"日付が変更されました。旧日付: {current_date}, 新日付: {today}")  # 日付変更のログ
        monthly_message_count.clear()
        current_date = today
        save_data()
        logging.info("メッセージ数がリセットされました。")
    else:
        logging.info("日付は変更されていません。")

scheduler = AsyncIOScheduler()
scheduler.add_job(reset_daily_tasks, CronTrigger(hour=0, minute=0, timezone=timezone("Asia/Tokyo")))

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    user_id = message.author.id
    today = current_date

    # メッセージを投稿するごとにポイントを30追加
    user_points[user_id] += 30
    monthly_message_count[user_id] += 1
    save_data()  # データの保存

    bonus_message = check_and_give_login_bonus(user_id, today)
    if bonus_message:
        await message.author.send(f'{bonus_message} 現在のポイント: {user_points[user_id]} 🪙')

    # 通常のメッセージ処理
    await bot.process_commands(message)

@bot.event
async def on_reaction_add(reaction, user):
    if user == bot.user:
        return

    user_id = user.id
    today = datetime.datetime.now(timezone("Asia/Tokyo")).date()

    logging.info(f'リアクション検出: user_id={user_id}, reaction={reaction.emoji}, message_id={reaction.message.id}')
    # リアクションするごとにポイントを5追加
    user_points[user_id] += 5
    save_data()  # データの保存

    bonus_message = check_and_give_login_bonus(user_id, today)
    if bonus_message:
        await user.send(f'{bonus_message} 現在のポイント: {user_points[user_id]} 🪙')

@bot.tree.command(name="ポイント", description="現在のポイントを表示します")
@app_commands.describe(member="ポイントを確認するメンバー")
async def points(interaction: discord.Interaction, member: discord.Member = None):
    if member:
        user_id = member.id
        points = user_points[user_id]
        await interaction.response.send_message(f'{member.mention} のポイント: {points} 🪙', ephemeral=True)
    else:
        user_id = interaction.user.id
        points = user_points[user_id]
        await interaction.response.send_message(f'{interaction.user.mention} あなたのポイント: {points} 🪙', ephemeral=True)

# ポイント贈答の部分を以下に修正
@bot.tree.command(name="ポイント贈答", description="他のメンバーにポイントをプレゼントします")
@app_commands.describe(member="ポイントを贈るメンバー", points="贈答するポイント数")
async def give_points(interaction: discord.Interaction, member: discord.Member, points: int):
    giver_id = interaction.user.id
    if giver_id in ADMIN_USER_IDS or user_points[giver_id] >= points:
        user_points[member.id] += points
        if giver_id not in ADMIN_USER_IDS:
            user_points[giver_id] -= points
        save_data()  # データの保存
        await interaction.response.send_message(f'{member.mention} に {points} 🪙 ポイントをプレゼントしました。相手の現在のポイント: {user_points[member.id]} 🪙')
    else:
        await interaction.response.send_message(f'ポイントが足りません。現在の所持ポイント: {user_points[giver_id]} 🪙', ephemeral=True)

# ランキングの部分を以下に修正
@bot.tree.command(name="ランキング", description="所持ポイント数のランキングを表示します")
async def ranking(interaction: discord.Interaction):
    guild = interaction.guild  # サーバー（ギルド）情報を取得
    rankings = sorted([(user_id, points) for user_id, points in user_points.items() if user_id not in ADMIN_USER_IDS], key=lambda x: x[1], reverse=True)[:5]
    response = "**ポイントランキング**\n"
    for i, (user_id, points) in enumerate(rankings):
        member = guild.get_member(user_id)
        if member:
            display_name = member.display_name
        else:
            try:
                user = await bot.fetch_user(user_id)
                display_name = user.name  # display_nameではなくnameを使用する
            except:
                display_name = "Unknown User"
        response += f'{i+1}. {display_name}: {points} 🪙\n'
    await interaction.response.send_message(response, ephemeral=True)


@bot.tree.command(name="コマンド_説明", description="使用できるコマンド一覧とポイントの説明を表示します")
async def show_commands_description(interaction: discord.Interaction):
    commands_list = """
    **使用可能なコマンド一覧**
    /ポイント - 現在のポイントを表示 🪙
    /ポイント贈答 - 他のメンバーにポイントをプレゼント 🎁
    /ランキング - 所持ポイント数のランキングを表示 👑
    /コマンド_説明 - 使用できるコマンド一覧とポイントの説明を表示
    /ショップ - 商品交換リンクを表示 🛒
    これらのコマンドを送ると、ワレカラくんがあなただけに見えるメッセージを送ります📩（ポイント贈答は他のメンバーにも見えます）
    
    **ポイントの説明**
    その日初めてメッセージを送った時、もしくはその日初めて誰かにリアクション（絵文字のスタンプ）した時に50ポイント、1メッセージ送るごとに30ポイント、誰かにリアクションするごとに5ポイントをワレカラくんから貰えます🪙
    さらに、連続3日ログイン（メッセージorリアクション）したら50ポイント、5日で100ポイント、10日で200ポイントの連続ボーナスを追加でプレゼント🎁
    貯まったポイントは「/ショップ」で商品と交換できます🛒
    「良いこと言ってるな！」と思ったゼミ生には「/ポイント贈答」でポイントをプレゼントしちゃいましょう🎁
    """
    
    await interaction.response.send_message(commands_list, ephemeral=True)

@bot.tree.command(name="ショップ", description="商品交換リンクを表示します")
async def shop(interaction: discord.Interaction):
    response = "リンク先から交換可能なアイテム一覧をご確認ください🛒\nhttps://forms.gle/gtUC7Au8KfWenXrD6"
    await interaction.response.send_message(response, ephemeral=True)

# 管理者向けのポイントマイナス機能
@bot.tree.command(name="ポイント減算", description="ザッキーのみ使用可能。ポイントを減算します")
@app_commands.describe(member="ポイントを減算するメンバー", points="減算するポイント数")
async def subtract_points(interaction: discord.Interaction, member: discord.Member, points: int):
    if interaction.user.id in ADMIN_USER_IDS:
        user_points[member.id] -= points
        save_data()  # データの保存
        await member.send(f'{interaction.user.name}が{points}ポイントを引きました。')
        await interaction.response.send_message(f'{member.mention}のポイントが{points}減りました。', ephemeral=True)
    else:
        await interaction.response.send_message('このコマンドを実行する権限がありません。', ephemeral=True)

if __name__ == "__main__":
    from http.server import HTTPServer, BaseHTTPRequestHandler
    import threading

    class SimpleHTTPRequestHandler(BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"Server is running")

    def run_server():
        server = HTTPServer(('0.0.0.0', 8000), SimpleHTTPRequestHandler)
        server.serve_forever()

    threading.Thread(target=run_server).start()
    bot.run(DISCORD_BOT_TOKEN)
