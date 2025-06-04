import discord
import requests
from bs4 import BeautifulSoup
import asyncio
import datetime
import pytz
import os

TOKEN = os.getenv("DISCORD_TOKEN")
URL = 'https://growagarden.gg/stocks'
CHANNEL_ID = 1377545700157690078

intents = discord.Intents.default()
client = discord.Client(intents=intents)

async def fetch_stock_data():
    """Fetch and format all stock categories."""
    headers = {"User-Agent": "Mozilla/5.0"}
    response = requests.get(URL, headers=headers)
    soup = BeautifulSoup(response.text, 'html.parser')

    stock_headers = [
        "Gear Stock", "Egg Stock", "Seeds Stock",
        "Honey Stock", "Cosmetics Stock"
    ]

    embed = discord.Embed(
        title="Stock Update",
        color=discord.Color.green()
    )

    # Add timestamp
    ph_tz = pytz.timezone("Asia/Manila")
    now = datetime.datetime.now(ph_tz).strftime("%Y-%m-%d %H:%M:%S")
    embed.set_footer(text=f"Updated at {now} PHT")

    mention_everyone = False  # Flag to trigger @everyone mention

    for header in stock_headers:
        stock_content = ""

        # Locate the correct section for each stock category
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

                        # Check for important stock items
                        if (
                            (header == "Gear Stock" and "Master Sprinkler" in name) or
                            (header == "Seeds Stock" and "Beanstalk" in name) or
                            (header == "Egg Stock" and ("Mythical Egg" in name or "Bug Egg" in name))
                        ):
                            mention_everyone = True
            else:
                stock_content = "❌ No items available"
        else:
            stock_content = "❌ Stock category not found"

        embed.add_field(name=header, value=stock_content, inline=False)

    return embed, mention_everyone

async def update_stock_message(channel):
    """Updates the stock message at precise 5-minute and 30-second intervals."""
    await client.wait_until_ready()
    stock_message = await channel.send(embed=discord.Embed(title="Loading stock data...", color=discord.Color.red()))

    while True:
        try:
            new_embed, mention_everyone = await fetch_stock_data()
            await stock_message.edit(embed=new_embed)

            # Notify @everyone if any target item is found
            if mention_everyone:
                await channel.send("@everyone 🚨 A high-value item is now in stock! 🚨")

            # Sync updates to exact 5-minute and 30-second marks
            ph_tz = pytz.timezone("Asia/Manila")
            now = datetime.datetime.now(ph_tz)

            next_update_minute = ((now.minute // 5 + 1) * 5) % 60
            next_update = now.replace(minute=next_update_minute, second=30, microsecond=0)

            if next_update <= now:
                next_update += datetime.timedelta(minutes=5)

            wait_seconds = (next_update - now).total_seconds()
            await asyncio.sleep(wait_seconds)

        except Exception as e:
            error_embed = discord.Embed(
                title="Error Fetching Data",
                description=str(e),
                color=discord.Color.red()
            )
            await stock_message.edit(embed=error_embed)

@client.event
async def on_ready():
    print(f'Logged in as {client.user}')
    channel = client.get_channel(CHANNEL_ID)

    if channel:
        client.loop.create_task(update_stock_message(channel))

client.run(TOKEN)
