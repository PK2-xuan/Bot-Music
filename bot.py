import os
import discord
from discord.ext import commands
from discord import app_commands
from dotenv import load_dotenv
import yt_dlp
from collections import deque
import asyncio
import time

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

SONG_QUEUES = {}
LAST_ACTIVITY_TIME = {}

async def search_ytdlp_async(query, ydl_opts):
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, lambda: _extract(query, ydl_opts))

def _extract(query, ydl_opts):
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        return ydl.extract_info(query, download=False)

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"{bot.user} is online!")

@bot.tree.command(name="skip", description="Salta la canción que está sonando.")
async def skip(interaction: discord.Interaction):
    if interaction.guild.voice_client and (interaction.guild.voice_client.is_playing() or interaction.guild.voice_client.is_paused()):
        interaction.guild.voice_client.stop()
        await interaction.response.send_message("¡Canción saltada!")
    else:
        await interaction.response.send_message("No hay ninguna canción para saltar.")

@bot.tree.command(name="pause", description="Pausa la canción que está sonando.")
async def pause(interaction: discord.Interaction):
    voice_client = interaction.guild.voice_client
    if voice_client is None:
        return await interaction.response.send_message("No estoy en un canal de voz.")
    if not voice_client.is_playing():
        return await interaction.response.send_message("No hay ninguna canción sonando.")
    voice_client.pause()
    await interaction.response.send_message("¡Reproducción pausada!")

@bot.tree.command(name="resume", description="Reanuda la canción pausada.")
async def resume(interaction: discord.Interaction):
    voice_client = interaction.guild.voice_client
    if voice_client is None:
        return await interaction.response.send_message("No estoy en un canal de voz.")
    if not voice_client.is_paused():
        return await interaction.response.send_message("No estoy pausado en este momento.")
    voice_client.resume()
    await interaction.response.send_message("¡Reproducción reanudada!")

@bot.tree.command(name="stop", description="Detiene la reproducción y limpia la cola.")
async def stop(interaction: discord.Interaction):
    voice_client = interaction.guild.voice_client
    if not voice_client or not voice_client.is_connected():
        return await interaction.response.send_message("No estoy conectado a ningún canal de voz.")
    guild_id_str = str(interaction.guild_id)
    if guild_id_str in SONG_QUEUES:
        SONG_QUEUES[guild_id_str].clear()
    if voice_client.is_playing() or voice_client.is_paused():
        voice_client.stop()
    await voice_client.disconnect()
    await interaction.response.send_message("Reproducción detenida y desconectado.")

@bot.tree.command(name="play", description="Reproduce una canción o agrégala a la cola.")
@app_commands.describe(song_query="Consulta de búsqueda")
async def play(interaction: discord.Interaction, song_query: str):
    await interaction.response.defer()
    voice_channel = interaction.user.voice.channel if interaction.user.voice else None
    if voice_channel is None:
        await interaction.followup.send("Debes estar en un canal de voz para reproducir música.")
        return
    voice_client = interaction.guild.voice_client
    if voice_client is None:
        voice_client = await voice_channel.connect()
    elif voice_channel != voice_client.channel:
        await voice_client.move_to(voice_channel)

    ydl_options = {
        "format": "bestaudio[abr<=96]/bestaudio",
        "noplaylist": True,
        "youtube_include_dash_manifest": False,
        "youtube_include_hls_manifest": False,
    }

    query = "ytsearch1: " + song_query
    results = await search_ytdlp_async(query, ydl_options)
    tracks = results.get("entries", [])

    if not tracks:
        await interaction.followup.send("No se encontraron resultados.")
        return

    first_track = tracks[0]
    audio_url = first_track["url"]
    title = first_track.get("title", "Sin título")

    guild_id = str(interaction.guild_id)
    if guild_id not in SONG_QUEUES:
        SONG_QUEUES[guild_id] = deque()

    SONG_QUEUES[guild_id].append((audio_url, title))

    if voice_client.is_playing() or voice_client.is_paused():
        await interaction.followup.send(f"Agregado a la cola: **{title}**")
    else:
        await interaction.followup.send(f"Ahora reproduciendo: **{title}**")
        await play_next_song(voice_client, guild_id, interaction.channel)

async def play_next_song(voice_client, guild_id, channel):
    LAST_ACTIVITY_TIME[guild_id] = time.time()
    if SONG_QUEUES[guild_id]:
        audio_url, title = SONG_QUEUES[guild_id].popleft()
        ffmpeg_options = {
            "before_options": "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5",
            "options": "-vn -c:a libopus -b:a 96k",
        }
        source = discord.FFmpegOpusAudio(audio_url, **ffmpeg_options, executable="bin\\ffmpeg\\bin\\ffmpeg.exe")

        def after_play(error):
            if error:
                print(f"Error al reproducir {title}: {error}")
            asyncio.run_coroutine_threadsafe(play_next_song(voice_client, guild_id, channel), bot.loop)

        voice_client.play(source, after=after_play)
        asyncio.create_task(channel.send(f"Reproduciendo: **{title}**"))
    else:
        if time.time() - LAST_ACTIVITY_TIME[guild_id] > 600:
            await voice_client.disconnect()
            await channel.send("Me he desconectado por inactividad.")
        else:
            await channel.send("No hay más canciones en la cola. El bot permanecerá en el canal.")

bot.run(TOKEN)
