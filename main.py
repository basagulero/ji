import discord
import asyncio
import datetime
import pytz
import math
import os
from playwright.async_api import async_playwright

# === Configuration ===
TOKEN = os.getenv("DISCORD_TOKEN")
URL = "https://growagardenstock.org/"
CHANNEL_ID = 1377545700157690078
PHT = pytz.timezone("Asia/Manila")
REFRESH_INTERVAL_SECONDS = 360  # 6 minutes

# === Discord Setup ===
intents = discord.Intents.default()
client = discord.Client(intents=intents)

# === Globals ===
task_started = False
last_egg_mention_time_pht = None

emoji_map = {
    "Mythical Egg": "🥚",
    "Bug Egg": "🐞",
    "Legendary Egg": "🌟",
    "Beanstalk": "🌱",
    "Ember Lily": "🔥",
    "Sugar Apple": "🍎",
    "Master Sprinkler": "💧"
}


def get_next_aligned_time(interval_seconds: int, timezone) -> int:
    now = datetime.datetime.now(timezone)
    total_seconds_today = now.hour * 3600 + now.minute * 60 + now.second
    next_multiple = math.ceil(total_seconds_today / interval_seconds) * interval_seconds
    return next_multiple - total_seconds_today


async def scrape_stock_data():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()

        try:
            await page.goto(URL, timeout=60000)
            await page.wait_for_selector("#growAGardenStockTracker", timeout=30000)
        except Exception as e:
            print(f"❌ Failed to load or find stock section: {e}")
            await browser.close()
            return []

        stocks = await page.evaluate("""
            () => {
                const values = Object.values(window);
                for (let v of values) {
                    if (Array.isArray(v)) {
                        for (let entry of v) {
                            if (typeof entry === 'string' && entry.includes('"stocks":')) {
                                try {
                                    const match = entry.match(/"stocks":({.*?})/);
                                    if (match) {
                                        return JSON.parse(match[1]);
                                    }
                                } catch (e) {
                                    return null;
                                }
                            }
                        }
                    }
                }
                return null;
            }
        """)

        await browser.close()

        if not stocks:
            print("❌ No stock data found.")
            return []

        formatted = []
        for header, items in stocks.items():
            stock_list = [(item["name"], str(item["value"]), item.get("image")) for item in items]
            formatted.append((header, stock_list))

        return formatted


async def fetch_stock_data():
    global last_egg_mention_time_pht

    embed = discord.Embed(title="🌱 Grow a Garden - Stock Update", color=discord.Color.green())
    now_str = datetime.datetime.now(PHT).strftime("%Y-%m-%d %H:%M:%S")
    embed.set_footer(text=f"Updated at {now_str} PHT")

    mention_everyone = False
    special_mention_messages = []

    for attempt in range(20):
        stock_data = await scrape_stock_data()
        if all(len(items) > 0 for _, items in stock_data):
            break
        print(f"⏳ Retry #{attempt + 1} - Incomplete stock data.")
        await asyncio.sleep(5)
    else:
        raise RuntimeError("Failed to fetch valid stock data after 20 attempts.")

    for header, items in stock_data:
        stock_content = ""
        for name, quantity, _ in items:
            emoji = emoji_map.get(name, "🔹")
            stock_content += f"{emoji} {name} ({quantity})\n"

            # === Mentions based on item type ===
            if header == "Gear Stock" and "Master Sprinkler" in name:
                mention_everyone = True
                special_mention_messages.append("@everyone 💧 Master Sprinkler is now in stock!")

            elif header == "Egg Stock":
                now_pht = datetime.datetime.now(PHT)
                can_mention = (
                    last_egg_mention_time_pht is None or
                    (now_pht - last_egg_mention_time_pht).total_seconds() >= 1920
                )
                if can_mention:
                    if "Mythical Egg" in name:
                        special_mention_messages.append("@everyone 🥚 Mythical Egg is in stock!")
                        mention_everyone = True
                    elif "Bug Egg" in name:
                        special_mention_messages.append("@everyone 🐞 Bug Egg is in stock!")
                        mention_everyone = True
                    elif "Legendary Egg" in name:
                        special_mention_messages.append("@everyone 🌟 Legendary Egg is in stock!")
                        mention_everyone = True
                    last_egg_mention_time_pht = now_pht

            elif header == "Seeds Stock":
                if "Beanstalk" in name:
                    special_mention_messages.append("@everyone 🌱 Beanstalk seed is in stock!")
                elif "Ember Lily" in name:
                    special_mention_messages.append("@everyone 🔥 Ember Lily seed is in stock!")
                elif "Sugar Apple" in name:
                    special_mention_messages.append("@everyone 🍎 Sugar Apple seed is in stock!")
                if any(seed in name for seed in ["Beanstalk", "Ember Lily", "Sugar Apple"]):
                    mention_everyone = True

        embed.add_field(
            name=header.upper(),
            value=stock_content if stock_content else "❌ No items available",
            inline=False
        )

    return embed, mention_everyone, special_mention_messages


async def update_stock_message(channel):
    await client.wait_until_ready()
    stock_message = await channel.send(embed=discord.Embed(title="Loading stock data...", color=discord.Color.red()))

    while True:
        try:
            embed, should_mention, mentions = await fetch_stock_data()
            await stock_message.edit(embed=embed)

            if should_mention and mentions:
                await channel.send("\n".join(mentions))

        except Exception as e:
            print(f"❌ Exception: {e}")
            await stock_message.edit(embed=discord.Embed(
                title="Error Fetching Data",
                description=str(e),
                color=discord.Color.red()
            ))

        sleep_duration = get_next_aligned_time(REFRESH_INTERVAL_SECONDS, PHT)
        await asyncio.sleep(sleep_duration)


@client.event
async def on_ready():
    global task_started
    print(f"✅ Logged in as {client.user}")
    channel = client.get_channel(CHANNEL_ID)

    if not channel:
        print(f"⚠️ Channel ID {CHANNEL_ID} not found or no permission.")
        return

    if not task_started:
        task_started = True
        client.loop.create_task(update_stock_message(channel))


if not TOKEN:
    raise EnvironmentError("DISCORD_TOKEN is not set in environment.")

client.run(TOKEN)
