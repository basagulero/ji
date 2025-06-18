import discord
import asyncio
import datetime
import pytz
import math
import os
from playwright.async_api import async_playwright

TOKEN = os.getenv("DISCORD_TOKEN")
URL = "https://growagardenstock.org/"
CHANNEL_ID = 1377545700157690078

intents = discord.Intents.default()
client = discord.Client(intents=intents)

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

def get_next_aligned_time(interval_seconds, timezone):
    now = datetime.datetime.now(timezone)
    total_seconds_today = now.hour * 3600 + now.minute * 60 + now.second
    next_multiple = math.ceil(total_seconds_today / interval_seconds) * interval_seconds
    return next_multiple - total_seconds_today

async def scrape_stock_data():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/113.0.0.0 Safari/537.36")
        page = await context.new_page()
        await page.goto(URL, timeout=60000)

        try:
            await page.wait_for_selector("div.bg-slate-800\\2f 50.border", timeout=30000)
        except:
            print("❌ Timeout waiting for stock sections.")
            return []

        sections = await page.query_selector_all("div.bg-slate-800\\2f 50.border")
        data = []

        for section in sections:
            try:
                header = await section.query_selector("h3")
                header_text = (await header.inner_text()).strip()

                if header_text == "Seeds Stock":
                    item_divs = await section.query_selector_all("div.p-4 > div > div.flex.items-center.gap-3")
                else:
                    item_divs = await section.query_selector_all("div.flex.items-center.gap-3")

                retries = 0
                while len(item_divs) == 0 and retries < 5:
                    await asyncio.sleep(3)
                    if header_text == "Seeds Stock":
                        item_divs = await section.query_selector_all("div.p-4 > div > div.flex.items-center.gap-3")
                    else:
                        item_divs = await section.query_selector_all("div.flex.items-center.gap-3")
                    retries += 1

                stock_list = []
                for item in item_divs:
                    try:
                        name_elem = await item.query_selector("span.font-medium")
                        qty_elem = await item.query_selector("span.font-semibold")
                        img_elem = await item.query_selector("img")

                        name = (await name_elem.inner_text()).strip()
                        qty = (await qty_elem.inner_text()).strip()
                        icon = await img_elem.get_attribute("src") if img_elem else None

                        stock_list.append((name, qty, icon))
                    except:
                        continue

                data.append((header_text, stock_list))
            except:
                continue

        await browser.close()
        return data

async def fetch_stock_data():
    global last_egg_mention_time_pht

    embed = discord.Embed(
        title="🌱 Grow a Garden - Stock Update",
        color=discord.Color.green()
    )

    ph_tz = pytz.timezone("Asia/Manila")
    now = datetime.datetime.now(ph_tz).strftime("%Y-%m-%d %H:%M:%S")
    embed.set_footer(text=f"Updated at {now} PHT")

    mention_everyone = False
    special_mention_messages = []

    tries = 0
    stock_data = []
    while tries < 20:
        stock_data = await scrape_stock_data()
        if all(len(items) > 0 for _, items in stock_data):
            break
        print("⏳ Retrying stock fetch...")
        await asyncio.sleep(5)
        tries += 1

    for header, items in stock_data:
        stock_content = ""
        for name, quantity, _ in items:
            emoji = emoji_map.get(name, "🔹")
            stock_content += f"{emoji} {name} ({quantity})\n"

            if header == "Gear Stock" and "Master Sprinkler" in name:
                mention_everyone = True
                special_mention_messages.append("@everyone 💧 Master Sprinkler is now in stock!")

            elif header == "Egg Stock":
                now_pht = datetime.datetime.now(ph_tz)
                can_mention = (
                    last_egg_mention_time_pht is None or
                    (now_pht - last_egg_mention_time_pht).total_seconds() >= 1920
                )
                triggered = False
                if can_mention:
                    if "Mythical Egg" in name:
                        special_mention_messages.append("@everyone 🥚 Mythical Egg is in stock!")
                        triggered = True
                    elif "Bug Egg" in name:
                        special_mention_messages.append("@everyone 🐞 Bug Egg is in stock!")
                        triggered = True
                    elif "Legendary Egg" in name:
                        special_mention_messages.append("@everyone 🌟 Legendary Egg is in stock!")
                        triggered = True
                if triggered:
                    mention_everyone = True
                    last_egg_mention_time_pht = now_pht

            elif header == "Seeds Stock":
                if "Beanstalk" in name:
                    special_mention_messages.append("@everyone 🌱 Beanstalk seed is in stock!")
                    mention_everyone = True
                elif "Ember Lily" in name:
                    special_mention_messages.append("@everyone 🔥 Ember Lily seed is in stock!")
                    mention_everyone = True
                elif "Sugar Apple" in name:
                    special_mention_messages.append("@everyone 🍎 Sugar Apple seed is in stock!")
                    mention_everyone = True

        if stock_content:
            embed.add_field(name=header.upper(), value=stock_content, inline=False)
        else:
            embed.add_field(name=header.upper(), value="❌ No items available", inline=False)

    return embed, mention_everyone, special_mention_messages

async def update_stock_message(channel):
    await client.wait_until_ready()
    stock_message = await channel.send(embed=discord.Embed(title="Loading stock data...", color=discord.Color.red()))

    while True:
        try:
            embed, mention_everyone, mention_msgs = await fetch_stock_data()
            await stock_message.edit(embed=embed)
            if mention_everyone and mention_msgs:
                await channel.send("\n".join(mention_msgs))

        except Exception as e:
            print(f"❌ Error: {e}")
            await stock_message.edit(embed=discord.Embed(
                title="Error Fetching Data",
                description=str(e),
                color=discord.Color.red()
            ))

        sleep_time = get_next_aligned_time(360, pytz.timezone("Asia/Manila"))
        await asyncio.sleep(sleep_time)

@client.event
async def on_ready():
    global task_started
    print(f"✅ Logged in as {client.user}")
    channel = client.get_channel(CHANNEL_ID)

    if channel is None:
        print(f"⚠️ Channel ID {CHANNEL_ID} not found or bot lacks permission.")
        return

    if not task_started:
        task_started = True
        client.loop.create_task(update_stock_message(channel))

if not TOKEN:
    raise EnvironmentError("DISCORD_TOKEN is not set in environment.")

client.run(TOKEN)
