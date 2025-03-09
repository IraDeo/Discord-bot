import discord
from discord.ext import commands, tasks
import google.generativeai as genai
import asyncio
import yt_dlp
import datetime
import os
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-1.5-pro-latest") 

bot = commands.Bot(command_prefix="!", intents=discord.Intents.all())

music_queue = []
reminders = {}

@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user}")
    bot.loop.create_task(cleanup_reminders())  # ✅ Run reminder cleanup

@bot.command()
async def hello(ctx):
    await ctx.send("Hello! I am your bot 🤖")
# 🔹 AI Chat (Using Gemini API)

@bot.command()
async def chat(ctx, *, prompt: str):
    """Handles the !chat command to get a response from Gemini AI"""
    try:
        response = model.generate_content(prompt)  # Generate AI response
        await ctx.send(response.text)  # Send response to Discord
    except Exception as e:
        await ctx.send(f"❌ Error: {e}")

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
    """Summarize long messages using Gemini AI"""
    try:
        response = model.generate_content(f"Summarize this: {text}")  # ✅ Proper usage
        await ctx.send(f"📄 **Summary:** {response.text}")
    except Exception as e:
        await ctx.send(f"❌ Error: {e}")

# 🔹 Custom Welcome Messages
@bot.event
async def on_member_join(member):
    channel = discord.utils.get(member.guild.text_channels, name="general")
    if channel:
        await channel.send(f"👋 Welcome {member.mention} to {member.guild.name}!")

# 🔹 Music Player (Queue System)
@bot.command()
async def play(ctx, url: str):
    """Plays music from a YouTube URL"""
    if not ctx.author.voice or not ctx.author.voice.channel:
        await ctx.send("❌ You must be in a voice channel!")
        return

    voice_channel = ctx.author.voice.channel
    if ctx.voice_client is None:
        voice = await voice_channel.connect()
    else:
        voice = ctx.voice_client

    music_queue.append(url)
    if not voice.is_playing():
        await play_next(ctx)
async def play_next(ctx):
    """Plays the next song in the queue"""
    if not music_queue:
        await ctx.send("🎵 Queue is empty, disconnecting.")
        await ctx.voice_client.disconnect()
        return

    url = music_queue.pop(0)

    ydl_opts = {
        'format': 'bestaudio/best',
        'noplaylist': True,
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
        audio_url = info['url']

    ffmpeg_options = {
        'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
        'options': '-vn',
    }

    ctx.voice_client.play(
        discord.FFmpegPCMAudio(audio_url, **ffmpeg_options),
        after=lambda e: asyncio.run_coroutine_threadsafe(play_next(ctx), bot.loop)
    )

    await ctx.send(f"🎶 Now playing: **{info['title']}**")

@bot.command()
async def queue(ctx):
    """Shows the current queue"""
    if music_queue:
        queue_list = "\n".join([f"{i+1}. {url}" for i, url in enumerate(music_queue)])
        await ctx.send(f"🎵 **Music Queue:**\n{queue_list}")
    else:
        await ctx.send("🎵 The queue is empty.")

@bot.command()
async def skip(ctx):
    """Skips the current song"""
    if ctx.voice_client and ctx.voice_client.is_playing():
        ctx.voice_client.stop()
        await ctx.send("⏭ Skipping to the next song!")

@bot.command()
async def stop(ctx):
    """Stops music and disconnects the bot"""
    if ctx.voice_client:
        await ctx.voice_client.disconnect()
        await ctx.send("🔇 Stopped playing music.")

# Run the bot
bot.run(TOKEN)
