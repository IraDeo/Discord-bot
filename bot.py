import discord
from discord.ext import commands, tasks
import google.generativeai as genai
import asyncio
import yt_dlp
import datetime
import os

TOKEN = "MTM0Njg2MDQ3ODgzNTU5MzI1OAh.Gu4mYT.AIn_52ZrrksuzOabdw6-K8xfh2wyGFystxjnCO1c"
GEMINI_API_KEY = "AIzaSyAWsjdN4IswbniwcK6FVTgzu7PwsxddduX_H5dkFlo7U"

# Configure Gemini API
genai.configure(api_key=GEMINI_API_KEY)

# Bot setup
bot = commands.Bot(command_prefix="!", intents=discord.Intents.all())

# Music queue
music_queue = []
reminders = {}
# Set bot command prefix
bot = commands.Bot(command_prefix="!", intents=discord.Intents.all())

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user.name}")

@bot.command()
async def hello(ctx):
    await ctx.send("Hello! I am your bot 🤖")
# 🔹 AI Chat (Using Gemini API)
@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    # Process the !chat command manually
    if message.content.startswith("!chat "):
        prompt = message.content.replace("!chat ", "")
        model = genai.GenerativeModel("gemini-pro")  # model
        response = model.generate_content(prompt)    #get response
        await message.channel.send(response.text)    #send response to discord

    # ✅ Ensure bot processes other commands
    await bot.process_commands(message)

# 🔹 Polls
@bot.command()
async def poll(ctx, question: str, *options):
    if len(options) < 2:
        await ctx.send("Polls need at least two options!")
        return
    
    poll_msg = f"📊 **{question}**\n"
    emojis = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣"]
    
    for i, option in enumerate(options[:5]):
        poll_msg += f"{emojis[i]} {option}\n"

    msg = await ctx.send(poll_msg)
    for i in range(len(options[:5])):
        await msg.add_reaction(emojis[i])

# 🔹 Reminders
@bot.command()
async def remind(ctx, time: int, *, reminder: str):
    user = ctx.author
    reminders[user] = (datetime.datetime.now() + datetime.timedelta(seconds=time), reminder)
    await ctx.send(f"⏳ Reminder set for {time} seconds: {reminder}")
    
    await asyncio.sleep(time)
    await ctx.send(f"🔔 {user.mention}, reminder: {reminder}")
    del reminders[user]

# 🔹 Auto-Delete Expired Reminders
@tasks.loop(minutes=1)
async def cleanup_reminders():
    now = datetime.datetime.now()
    expired = [user for user, (time, _) in reminders.items() if time < now]
    for user in expired:
        del reminders[user]

# 🔹 AI-Powered Summaries
@bot.command()
async def summarize(ctx, *, text: str):
    response = genai.summarize(text)
    await ctx.send(f"📄 **Summary:** {response.text}")

# 🔹 Custom Welcome Messages
@bot.event
async def on_member_join(member):
    channel = discord.utils.get(member.guild.text_channels, name="general")
    if channel:
        await channel.send(f"👋 Welcome {member.mention} to {member.guild.name}!")

# 🔹 Music Player (Queue System)
@bot.command()
async def play(ctx, url: str):
    voice_channel = ctx.author.voice.channel
    if not voice_channel:
        await ctx.send("❌ You must be in a voice channel!")
        return

    voice = await voice_channel.connect() if not ctx.voice_client else ctx.voice_client
    music_queue.append(url)
    
    if not voice.is_playing():
        await play_next(ctx)

async def play_next(ctx):
    if music_queue:
        url = music_queue.pop(0)
        ydl_opts = {'format': 'bestaudio'}
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            url2 = info['url']
        
        ffmpeg_opts = {'options': '-vn'}
        ctx.voice_client.play(discord.FFmpegPCMAudio(url2, **ffmpeg_opts), after=lambda e: asyncio.run(play_next(ctx)))

@bot.command()
async def queue(ctx):
    if music_queue:
        queue_list = "\n".join([f"{i+1}. {url}" for i, url in enumerate(music_queue)])
        await ctx.send(f"🎵 **Music Queue:**\n{queue_list}")
    else:
        await ctx.send("🎵 The queue is empty.")

@bot.command()
async def skip(ctx):
    if ctx.voice_client and ctx.voice_client.is_playing():
        ctx.voice_client.stop()
        await ctx.send("⏭ Skipping to the next song!")
        await play_next(ctx)

@bot.command()
async def stop(ctx):
    if ctx.voice_client:
        await ctx.voice_client.disconnect()
        await ctx.send("🔇 Stopped playing music.")

# Run the bot
@bot.event
async def on_ready():
    print(f"Logged in as {bot.user.name}")
    bot.loop.create_task(cleanup_reminders())  # ✅ Fixes the coroutine warning

bot.run(TOKEN)
