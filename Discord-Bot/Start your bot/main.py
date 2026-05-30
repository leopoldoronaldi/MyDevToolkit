import discord
import os
import asyncio
from discord.ext import commands

TOKEN = "YOUR_BOT_TOKEN" # Place your bot token here
COG_DIR = "cogs" # Directory containing extension files

intents = discord.Intents.default()
intents.message_content = False 

bot = commands.Bot(command_prefix="", intents=intents)

async def load_extensions():
    for filename in os.listdir(f'./{COG_DIR}'):
        if filename.endswith('.py'):
            try:
                await bot.load_extension(f'{COG_DIR}.{filename[:-3]}')
                print(f"[LOG] Loaded extension: {filename}")
            except Exception as e:
                print(f"[ERROR] Failed to load {filename}: {e}")

@bot.event
async def on_ready():
    print(f"[LOG] {bot.user} Bot online")
    
    await load_extensions()
    
    try:
        synced = await bot.tree.sync()
        print(f"[LOG] Successfully synced {len(synced)} slash command(s).")
    except Exception as e:
        print(f"[ERROR] Sync failed: {e}")

async def main():
    async with bot:
        await bot.start(TOKEN)

if __name__ == "__main__":
    asyncio.run(main())
