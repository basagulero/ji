import discord
import requests
from bs4 import BeautifulSoup
import asyncio
import datetime
import pytz
import os

TOKEN = os.getenv("DISCORD_TOKEN")  # Make sure your token is set in environment variables
URL = 'https://growagarden.gg/stocks'
CHANNEL_ID = 1377545700157690078  # Replace with your actual channel ID

intents = discord.Intents.default()
client = discord.Client(intents=intents)

task_started = False  # Prevent multiple tasks from starting

async def fetch_stock_data():
    """Fetch and format all stock categories from the website."""
    headers = {"User-Agent": "Mozilla/5.0"}
    response = requests.get(URL, headers=headers)
    soup = BeautifulSoup(response.text, 'html.parser')

    stock_headers = [
        "Gear Stock", "Egg Stock", "Seeds Stock",
        "Honey Stock", "Cosmetics Stock"
    ]

    embed = discord.Embed(
        title="🌱 Grow a Garden - Stock Update",
        color=discord.Color.green()
    )

    # Timestamp in Philippine Time
    ph_tz = pytz.timezone("Asia/Manila")
    now = datetime.datetime.now(ph_tz).strftime("%Y-%m-%d %H:%M:%S")
    embed.set_footer(text=f"Updated at {now} PHT")

    mention_everyone = False

    for header in stock_headers:
        stock_content = ""
        section = soup.find("h2", string=header)
        if section:
            items = section.find_next("section").find_all("article")
            if items:
                for item in items:
                    name_tag = item.select_one("h3")
                    quantity_tag = item.select_one("data")
                    if name_tag and quantity_tag:
                        name = name_tag.text.strip()
                        quantity = quantity_tag.text.strip()
                        stock_content += f"🔹 {name} ({quantity})\n"
                        if header == "Gear Stock" and "Master Sprinkler" in name:
                            mention_everyone = True
            else:
                stock_content = "❌ No items available"
        else:
            stock_content = "❌ Stock category not found"
        
        embed.add_field(name=header, value=stock_content, inline=False)

    return embed, mention_everyone

async def update_stock_message(channel):
    """Update the stock message every 6m30s and mention everyone if Master Sprinkler is in stock."""
    await client.wait_until_ready()
    stock_message = await channel.send(embed=discord.Embed(title="Loading stock data...", color=discord.Color.red()))

    while True:
        try:
            # Fetch and update
            new_embed, mention_everyone = await fetch_stock_data()
            await stock_message.edit(embed=new_embed)

            if mention_everyone:
                await channel.send("@everyone 🚨 Master Sprinkler is now in stock! 🚨")

            # Calculate next aligned time (6 minutes and 30 seconds)
            ph_tz = pytz.timezone("Asia/Manila")
            now = datetime.datetime.now(ph_tz)
            total_seconds = now.minute * 60 + now.second
            interval = 390  # 6 minutes 30 seconds
            next_seconds = ((total_seconds // interval) + 1) * interval
            next_time = now.replace(second=0, microsecond=0) + datetime.timedelta(seconds=(next_seconds - total_seconds))
            wait_time = (next_time - now).total_seconds()

            await asyncio.sleep(wait_time)

        except Exception as e:
            error_embed = discord.Embed(
                title="Error Fetching Data",
                description=str(e),
                color=discord.Color.red()
            )
            await stock_message.edit(embed=error_embed)

@client.event
async def on_ready():
    global task_started
    print(f'✅ Logged in as {client.user}')
    channel = client.get_channel(CHANNEL_ID)

    if channel and not task_started:
        task_started = True
        client.loop.create_task(update_stock_message(channel))

client.run(TOKEN)
