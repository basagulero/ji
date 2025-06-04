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
        "Honey Stock", "Cosmetics Stock"  # Updated headers
    ]

    embed = discord.Embed(
        title="Stock Update",
        color=discord.Color.green()
    )

    # Add timestamp
    ph_tz = pytz.timezone("Asia/Manila")
    now = datetime.datetime.now(ph_tz).strftime("%Y-%m-%d %H:%M:%S")
    embed.set_footer(text=f"Updated at {now} PHT")

    mention_everyone = False  # Track if "Master Sprinkler" is found

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

                        # Check if the Master Sprinkler is available
                        if header == "Gear Stock" and "Master Sprinkler" in name:
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

            # Notify @everyone if Master Sprinkler is found
            if mention_everyone:
                await channel.send("@everyone 🚨 Master Sprinkler is now in stock! 🚨")

            # Sync updates to exact 5-minute and 30-second marks
            ph_tz = pytz.timezone("Asia/Manila")
            now = datetime.datetime.now(ph_tz)

            next_update = (now.minute // 5 + 1) * 5
            wait_time = ((next_update - now.minute) * 60) - now.second + 30

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
    print(f'Logged in as {client.user}')
    channel = client.get_channel(CHANNEL_ID)

    if channel:
        client.loop.create_task(update_stock_message(channel))

client.run(TOKEN)
