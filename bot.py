import discord
from discord.ext import commands
from yt_dlp import YoutubeDL
from discord.ui import Button, View
import asyncio


bot = commands.Bot(command_prefix="/", intents=discord.Intents.all())

queue = []

FFMPEG_OPTIONS = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    'options': '-vn'
}

YDL_OPTIONS = {
    'format': 'bestaudio/best',
    'noplaylist': True,
    'quiet': True,
    'extract_flat': 'in_playlist'
}


@bot.event
async def on_ready():
    print(f"✅Bot {bot.user.name} has successfully started!")


@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    commands_to_delete = ["/play", "/join", "/leave", "/controls"]

    if any(command in message.content for command in commands_to_delete):
        await bot.process_commands(message)
        await asyncio.sleep(10)
        await message.delete()


@bot.event
async def on_voice_state_update(member): #before & after arguments
    voice_client = discord.utils.get(bot.voice_clients, guild=member.guild)
    if voice_client and not voice_client.is_playing() and queue:
        # next_song_url = queue.pop(0)
        # voice_client.play(discord.FFmpegPCMAudio(executable="ffmpeg", source=next_song_url, **FFMPEG_OPTIONS))
        # await member.guild.text_channels[0].send(f"🎶The next song in the queue is playing!", delete_after=10)
        await play_next(member.guild)


@bot.event
async def on_interaction(interaction):
    if interaction.type == discord.InteractionType.component:
        custom_id = interaction.data['custom_id']
        if custom_id == "skip":
            await interaction.response.defer()
            await skip(interaction)
        elif custom_id == "pause":
            await interaction.response.defer()
            await pause(interaction)
        elif custom_id == "resume":
            await interaction.response.defer()
            await resume(interaction)


@bot.command(name="join")
async def join(ctx):
    if ctx.author.voice:
        channel = ctx.author.voice.channel
        await channel.connect()
        msg = await ctx.send("🎵I joined the voice channel!")
        await asyncio.sleep(10)
        await msg.delete()
    else:
        msg = await ctx.send("🚫Join the voice channel first.")
        await asyncio.sleep(10)
        await msg.delete()


@bot.command(name="play")
async def play(ctx, url: str):
    voice_client = discord.utils.get(bot.voice_clients, guild=ctx.guild)

    if not voice_client:
        msg = await ctx.send("🚫First, add me to the voice channel with the `/join` command.")
        await asyncio.sleep(10)
        await msg.delete()
        return

    with YoutubeDL(YDL_OPTIONS) as ydl:
        try:
            info = ydl.extract_info(url, download=False)
            url2 = info['url']
            title = info.get('title', 'Untitled')
            queue.append((url2, title))
            await ctx.send(f"🎶Playing: **{title}**", delete_after=10)
            if not voice_client.is_playing():
                # voice_client.play(discord.FFmpegPCMAudio(executable="ffmpeg", source=url2, **FFMPEG_OPTIONS))
                await play_next(ctx.guild)

        except Exception as e:
            await ctx.send("🚫An error occurred while processing the link.")
            print(e)


async def play_next(guild):
    voice_client = discord.utils.get(bot.voice_clients, guild=guild)

    if queue and voice_client:
        next_song_url, next_song_title = queue.pop(0)

        def after_playing():
            fut = asyncio.run_coroutine_threadsafe(play_next(guild), bot.loop)
            try:
                fut.result()
            except Exception as e:
                print(f"Error in play_next: {e}")

        voice_client.play(
            discord.FFmpegPCMAudio(executable="ffmpeg", source=next_song_url, **FFMPEG_OPTIONS),
            # after=lambda e: asyncio.run_coroutine_threadsafe(play_next(guild), bot.loop)
            after=after_playing
        )
        channel = guild.text_channels[2] #the number of vc
        await channel.send(f"🎶Playing: **{next_song_title}**", delete_after=10)
    elif voice_client:
        await voice_client.disconnect()


@bot.command()
async def controls(ctx):
    button_skip = Button(label="Skip song", style=discord.ButtonStyle.primary, custom_id="skip")
    button_pause = Button(label="Pause song", style=discord.ButtonStyle.primary, custom_id="pause")
    button_resume = Button(label="Resume song", style=discord.ButtonStyle.primary, custom_id="resume")

    view = View()
    view.add_item(button_skip)
    view.add_item(button_pause)
    view.add_item(button_resume)

    await ctx.send("Choose one of the options:", view=view)


@bot.command()
async def skip(ctx):
    voice_client = discord.utils.get(bot.voice_clients, guild=ctx.guild)

    if voice_client and voice_client.is_playing():
        voice_client.stop()
        await ctx.send("Song skipped.", delete_after=10)

        # if queue:
        #     queue.pop(0)
        #
        #     if queue:
        #         next_song_url = queue[0]
        #         voice_client.play(discord.FFmpegPCMAudio(executable="ffmpeg", source=next_song_url, **FFMPEG_OPTIONS))
        #         await ctx.send(f"Playing next song: {next_song_url}", delete_after=10)

        await play_next(ctx.guild)


@bot.command()
async def pause(ctx):
    voice_client = discord.utils.get(bot.voice_clients, guild=ctx.guild)

    if voice_client and voice_client.is_playing():
        voice_client.pause()
        await ctx.send("The music is paused.", delete_after=10)


@bot.command()
async def resume(ctx):
    voice_client = discord.utils.get(bot.voice_clients, guild=ctx.guild)

    if voice_client and voice_client.is_paused():
        voice_client.resume()
        if voice_client and voice_client.is_playing():
            await ctx.send("The song had been resumed.", delete_after=10)
        else:
            await ctx.send("🚫No songs are paused.", delete_after=10)


@bot.command(name="leave")
async def leave(ctx):
    voice_client = discord.utils.get(bot.voice_clients, guild=ctx.guild)

    if voice_client:
        await voice_client.disconnect()
        await ctx.send("👋I left the voice channel.", delete_after=10)
    else:
        await ctx.send("🚫I'm not in the voice channel.")


bot.run("YOUR_TOKEN_HERE")
