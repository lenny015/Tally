import os
import re
import discord
from discord.ext import commands
from database import (db_init,
                      insert_guild,
                      get_current_number,
                      update_channel,
                      update_user_count,
                      get_leaderboard,
                      validate_channels,
                      delete_channel,
                      check_count_channel,
                      get_last_user,
                      get_channels_from_guild)
from dotenv import load_dotenv
from time import sleep
from typing import List

load_dotenv()

TOKEN = str(os.getenv('BOT_TOKEN'))

db_init()

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)
intents.message_content = True
intents.members = True

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user} with an ID of {bot.user.id}")
    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} commands")
    except Exception as e:
        print(e)
    
    validate_channels(bot)
    
@bot.event
async def on_guild_channel_delete(channel):
    if check_count_channel(str(channel.id)):
        delete_channel(str(channel.id))
    
@bot.tree.command(name="create-channel", description="Create a new moderated counting channel")
@discord.app_commands.describe(name='Gives the new counting channel a name. Defaults to "counting"')
async def create_channel(interaction: discord.Interaction, name: str = "counting"):
    await interaction.response.defer()
    guild = interaction.guild
    category = interaction.channel.category
    
    try:
        channel = await guild.create_text_channel(name=name, category=category, slowmode_delay=300)
        
        await channel.edit(position=0)
        
        insert_guild(str(guild.id), str(channel.id))
        update_channel(channel.id, 1)
        await interaction.followup.send(f"Created channel {channel.mention}.")
    except Exception as e:
        await interaction.followup.send(f"Failed to create channel: `{e}`")
        
@bot.event
async def on_message(message):
    if message.author.bot:
        return
    
    channel_id = str(message.channel.id)
    guild_id = str(message.guild.id)
    author_id = str(message.author.id)
    
    current_num = get_current_number(channel_id) + 1
    if current_num is not None:
        match = re.match(r'^(\d+)(?:\s.*)?$', message.content)
        if match:
            num = int(match.group(1))
            
            if num == current_num and (author_id != get_last_user(channel_id)):
                await message.add_reaction("✅")
                update_channel(channel_id, current_num + 1, message.author.id)
                update_user_count(author_id, guild_id, channel_id)
            else:
                await message.add_reaction("❌")
                sleep(0.3)
                await message.delete()
        else:
            await message.add_reaction("❌")
            sleep(0.3)
            await message.delete()
            
             
    await bot.process_commands(message)
    
@bot.tree.command(name="leaderboard", description="Show the leaderboard for the most active counters")
async def leaderboard(interaction: discord.Interaction):
    
    guild_id = str(interaction.guild.id)
    leaderboard = get_leaderboard(guild_id)
    
    if not leaderboard or leaderboard[0] == (None, None):
        em = discord.Embed(color=discord.Color.red())
        em.add_field(name="No users have counted yet.", value="")
        await interaction.response.send_message(embed=em)
    else:
        em = discord.Embed(
            title =  f'Top 10 Counters in {interaction.guild.name}',
            color=discord.Color.blue()
        )
        
        index = 1
        medals = [':first_place:', ':second_place:', ':third_place:']
        
        for user_id, count in leaderboard:
            if user_id is None:
                continue
            
            member = interaction.guild.get_member(int(user_id))
            
            if member:
                name = member.display_name
                
                if 1 <= index <= 3:
                    em.add_field(name=f"{medals[index-1]}`{name}` `{count}`", value="", inline=False)
                else:
                    em.add_field(name=f"`#{index}` `{name}` `{count}`", value="", inline=False)
            
            if index == 10:
                break
            index += 1
        
        await interaction.response.send_message(embed=em)
        
@bot.tree.command(name="current-number", description="Get the current number of a counting channel")
async def current_number(interaction: discord.Interaction, channel: str):
    
    ch = interaction.guild.get_channel(int(channel))
    
    if check_count_channel(channel) != None:
        curr = get_current_number(channel)
        em = discord.Embed(color=discord.Color.blue())
        em.add_field(name=f"The current number in {ch.mention} is {curr}", value="")
        
        await interaction.response.send_message(embed=em)
    else:
        em = discord.Embed(color=discord.Color.red())
        em.add_field(name=f"{ch.mention} is not a counting channel.", value="")
        await interaction.response.send_message(embed=em)
        
@current_number.autocomplete("channel")
async def counting_channels(interaction: discord.Interaction, channel_choices: str) -> List[discord.app_commands.Choice]:
    guild_id = str(interaction.guild.id)
    guild_channels = get_channels_from_guild(guild_id)
    
    choices = []
    for channel_id in guild_channels:
        channel = interaction.guild.get_channel(int(channel_id[0]))
        if isinstance(channel, discord.TextChannel):
            choices.append(discord.app_commands.Choice(name=channel.name, value=str(channel.id)))
            
    return choices
    
if __name__ == "__main__":
    bot.run(TOKEN)
