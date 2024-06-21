import discord
from discord import app_commands
from discord.ext import commands
from collections import defaultdict
import datetime
import json
import os

# 環境変数からトークンを取得
DISCORD_BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN")

# データファイルのパス
DATA_FILE = "user_data.json"

# インテントの設定
intents = discord.Intents.default()
intents.messages = True
intents.message_content = True  # メッセージ内容のインテントを有効にする
intents.guilds = True

bot = commands.Bot(command_prefix="!", intents=intents)

# ポイントとアイテムを保存する辞書
user_points = defaultdict(int)
user_items = defaultdict(list)
last_login_date = defaultdict(lambda: None)  # ユーザーの最終ログイン日を保存する辞書

# アイテムリストの定義（必要に応じて変更可能）
items = {
    "スタバ500円チケット（ザッキーが送ります）": 5000,  # アイテム名: 必要なポイント数
    "新しいアイテム2": 10000,
    "新しいアイテム3": 30000
}

def save_data():
    """ポイントとアイテムのデータを保存"""
    data = {
        "user_points": dict(user_points),
        "user_items": {k: v for k, v in user_items.items()},
        "last_login_date": {str(k): str(v) for k, v in last_login_date.items()}
    }
    with open(DATA_FILE, "w") as f:
        json.dump(data, f)
    print("データが保存されました: ", data)

def load_data():
    """ポイントとアイテムのデータを読み込む"""
    global user_points, user_items, last_login_date
    try:
        with open(DATA_FILE, "r") as f:
            data = json.load(f)
            user_points.update(data["user_points"])
            user_items.update(data["user_items"])
            last_login_date.update({int(k): datetime.datetime.fromisoformat(v).date() for k, v in data["last_login_date"].items()})
        print("データが読み込まれました: ", data)
    except FileNotFoundError:
        print("データファイルが見つかりません。新しいファイルを作成します。")
    except json.JSONDecodeError:
        print("データファイルの読み込みに失敗しました。JSON形式に問題があります。")

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}')
    try:
        synced = await bot.tree.sync()
        print(f'Synced {len(synced)} command(s)')
    except Exception as e:
        print(f'Failed to sync commands: {e}')
    load_data()  # データの読み込み
    print(f'ポイントデータ: {user_points}')  # 追加: ポイントデータの確認
    print(f'アイテムデータ: {user_items}')  # 追加: アイテムデータの確認

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    # メッセージを投稿するごとにポイントを30追加
    user_points[message.author.id] += 30
    save_data()  # データの保存

    # 日付が変わっていたらログインボーナスを付与
    today = datetime.datetime.utcnow().date()
    last_login = last_login_date[message.author.id]
    if last_login is None or last_login != today:
        user_points[message.author.id] += 100
        last_login_date[message.author.id] = today
        await message.author.send(f'ログインボーナスとして 100 🪙 ポイントを獲得しました！現在のポイント: {user_points[message.author.id]} 🪙')
        save_data()  # データの保存

    # 通常のメッセージ処理
    await bot.process_commands(message)

@bot.tree.command(name="ポイント", description="現在のポイントを表示します")
async def points(interaction: discord.Interaction):
    user_id = interaction.user.id
    points = user_points[user_id]
    print("ポイントを表示します: ", user_points)  # デバッグ用メッセージ
    await interaction.response.send_message(f'{interaction.user.mention} あなたのポイント: {points} 🪙', ephemeral=True)

@bot.tree.command(name="ポイント付与", description="他のメンバーにポイントを付与します")
@app_commands.describe(member="ポイントを付与するメンバー", points="付与するポイント数")
async def give_points(interaction: discord.Interaction, member: discord.Member, points: int):
    user_points[member.id] += points
    save_data()  # データの保存
    print("ポイント付与: ", user_points)  # デバッグ用メッセージ
    await interaction.response.send_message(f'{member.mention} に {points} 🪙 ポイントを付与しました。現在のポイント: {user_points[member.id]} 🪙')

@bot.tree.command(name="交換", description="ポイントを使用してアイテムを交換します")
@app_commands.describe(item_name="交換するアイテムの名前")
async def exchange(interaction: discord.Interaction, item_name: str):
    user_id = interaction.user.id
    if item_name in items:
        cost = items[item_name]
        if user_points[user_id] >= cost:
            user_points[user_id] -= cost
            user_items[user_id].append(item_name)
            response = f'{interaction.user.mention} さんが {cost} 🪙 ポイントで「{item_name}」を交換しました。残りのポイント: {user_points[user_id]} 🪙'
            await interaction.response.send_message(response, ephemeral=True)
            save_data()  # データの保存
            print("交換後のデータ: ", user_points, user_items)  # デバッグ用メッセージ
        else:
            response = f'{interaction.user.mention} さん、ポイントが不足しています。「{item_name}」を交換するには {cost} 🪙 ポイントが必要です。'
            await interaction.response.send_message(response, ephemeral=True)
    else:
        response = f'{interaction.user.mention} さん、指定されたアイテムは存在しません。利用可能なアイテム: {", ".join(items.keys())}'
        await interaction.response.send_message(response, ephemeral=True)

@bot.tree.command(name="アイテム", description="自分が保持しているアイテムを表示します")
async def show_items(interaction: discord.Interaction):
    user_id = interaction.user.id
    if user_items[user_id]:
        item_list = ', '.join(user_items[user_id])
        response = f'{interaction.user.mention} さんのアイテム: {item_list} 🎁'
        await interaction.response.send_message(response, ephemeral=True)
    else:
        response = f'{interaction.user.mention} さんはまだアイテムを持っていません。'
        await interaction.response.send_message(response, ephemeral=True)

@bot.tree.command(name="使用", description="保持しているアイテムを使用します")
@app_commands.describe(item_name="使用するアイテムの名前")
async def use_item(interaction: discord.Interaction, item_name: str):
    user_id = interaction.user.id
    if item_name in user_items[user_id]):
        user_items[user_id].remove(item_name)
        response = f'{interaction.user.mention} さんが「{item_name}」を使用しました。残りのアイテム: {", ".join(user_items[user_id])} 🎁'
        await interaction.response.send_message(response, ephemeral=True)
        save_data()  # データの保存
        print("使用後のデータ: ", user_points, user_items)  # デバッグ用メッセージ
        
        # アイテム使用の具体的な処理をここに追加
        # 例: ログに記録する
        with open("used_items_log.txt", "a") as log_file:
            log_file.write(f'{interaction.user} used {item_name} on {datetime.datetime.now()}\n')

        # さらに具体的な処理（例: カウンセリングの予約）
        if item_name == "カウンセリング一回追加チケット":
            # ここにカウンセリング予約の具体的な処理を記述
            await interaction.response.send_message(f'{interaction.user.mention} さん、カウンセリングの予約が完了しました。☝️', ephemeral=True)
    else:
        response = f'{interaction.user.mention} さんは「{item_name}」を持っていません。'
        await interaction.response.send_message(response, ephemeral=True)

@bot.tree.command(name="コマンド", description="使用できるコマンド一覧を表示します")
async def show_commands(interaction: discord.Interaction):
    commands_list = """
    **使用可能なコマンド一覧**
    /ポイント - 現在のポイントを表示します 🪙
    /ポイント付与 - 他のメンバーにポイントを付与します 🪙
    /交換 - ポイントを使用してアイテムを交換します ↔️
    /アイテム - 自分が保持しているアイテムを表示します 🎁
    /使用 - 保持しているアイテムを使用します 🎁
    /コマンド - 使用できるコマンド一覧を表示します
    /ショップ - 販売しているアイテムを表示します 🛒
    """
    await interaction.response.send_message(commands_list, ephemeral=True)

@bot.tree.command(name="ショップ", description="販売しているアイテムを表示します")
async def shop(interaction: discord.Interaction):
    shop_list = '\n'.join([f'{item}: {cost} 🪙' for item, cost in items.items()])
    await interaction.response.send_message(f'**ショップアイテム一覧**\n{shop_list} 🛒', ephemeral=True)

bot.run(DISCORD_BOT_TOKEN)
