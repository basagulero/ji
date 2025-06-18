import discord
from playwright.sync_api import sync_playwright
import asyncio
import datetime
import pytz
import os
import math

TOKEN = os.getenv("DISCORD_TOKEN")  # Set this in Railway's environment variables
URL = "https://growagardenstock.org/"
CHANNEL_ID = 1377545700157690078

intents = discord.Intents.default()
client = discord.Client(intents=intents)

task_started = False
last_egg_mention_time_pht = None

def get_next_aligned_time(interval_seconds, timezone):
    now = datetime.datetime.now(timezone)
    total_seconds_today = now.hour * 3600 + now.minute * 60 + now.second
    next_multiple = math.ceil(total_seconds_today / interval_seconds) * interval_seconds
    return next_multiple - total_seconds_today

def scrape_stock_data():
    data = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(URL, timeout=60000)
        page.wait_for_selector("div.bg-slate-800\\2f 50.border", timeout=15000)

        sections = page.query_selector_all("div.bg-slate-800\\2f 50.border")
        for section in sections:
            try:
                header = section.query_selector("h3").inner_text().strip()
                items = section.query_selector_all("div.flex.items-center.gap-3")
                stock_list = []

                for item in items:
                    try:
                        name = item.query_selector("span.font-medium").inner_text().strip()
                        qty = item.query_selector("span.font-semibold").inner_text().strip()
                        stock_list.append((name, qty))
                    except:
                        continue

                data.append((header, stock_list))
            except:
                continue

        browser.close()

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

    try:
        stock_data = await asyncio.to_thread(scrape_stock_data)
    except Exception as e:
        print("❌ Error during scraping:", e)
        embed.add_field(name="Error", value="Could not fetch data from website.", inline=False)
        return embed, False, []

    for header, items in stock_data:
        stock_content = ""
        for name, quantity in items:
            stock_content += f"🔹 {name} ({quantity})\n"

            if header == "Gear Stock" and "Master Sprinkler" in name:
                mention_everyone = True
                special_mention_messages.append("@everyone 🚨 Master Sprinkler is now in stock! 🚨")

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
            embed.add_field(name=header, value=stock_content, inline=False)
        else:
            embed.add_field(name=header, value="❌ No items available", inline=False)

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
