# Goose Bot Discord management tool meant for use by regular server members.
# Made by Gaelan O'Shea-McKay for personal non-commercial use.

# Import discord packages
import logging
import discord
from discord.ext import commands

# Import env file packages
import os
from dotenv import load_dotenv

# Import utils for the bot
import goose_bot_utils
import extended_emoji_dict

# Import sleep for some delays
from time import sleep

# Import datetime for upkeep messages
from datetime import datetime, time, timedelta
import asyncio

# Miscellaneous imports
from math import floor

# Load the bot token; The token is not to be made publicly available, so it is stored offline.
load_dotenv('environment.env')
BOT_TOKEN = os.getenv('BOT_TOKEN')

# Set up constants.
# The Message IDs will depend on the server and setup therein, so they are defined in the environment file.
GOOSE_BOT_COMMAND_PREFIX = '.'
GOOSE_BOT_DESCRIPTION = "A bot for basic server utilities."
REACTION_ROLE_MESSAGE_ID = os.getenv('REACTION_ROLE_MESSAGE_ID')
NOTIF_SUB_MESSAGE_ID = os.getenv('NOTIF_SUB_MESSAGE_ID')
SUB_CHANNEL_ID = os.getenv('SUB_CHANNEL_ID')
DAILY_MESSAGE_TIME = time(19, 0, 0)  # 12PM PST
DAILY_MESSAGE_CHANNEL_ID = int(os.getenv('DAILY_MESSAGE_CHANNEL_ID'))
HOURLY_MESSAGE_CHANNEL_ID = DAILY_MESSAGE_CHANNEL_ID
DAILY_MESSAGE = "Goose bot lives another day!"
HOURLY_MESSAGE = "Goose bot checking in."

# Set up required intents
intents = discord.Intents.default()
intents.typing = False
intents.presences = False
intents.members = True

# Set up the logger

LOG_FILE_NAME = "goose_bot_logs.log"
LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
logging.basicConfig(filename=LOG_FILE_NAME, format=LOG_FORMAT, level=logging.INFO)

# Initialize the client
client = discord.Client()

# Initialize the bot
goose_bot = commands.Bot(command_prefix=GOOSE_BOT_COMMAND_PREFIX, description=GOOSE_BOT_DESCRIPTION, intents=intents)

# Set the reaction messages and the emoji->role dict.
# The dict is kept in a private file because of irrelevant personal information, and a default dict is provided below.
channel_sub_message_id = REACTION_ROLE_MESSAGE_ID
notif_sub_message_id = NOTIF_SUB_MESSAGE_ID
emoji_to_role = extended_emoji_dict.emoji_to_role_extended


# Basic version of the emoji-> role dict, to use if you don't have a more personal one to supply in extended_emoji_dict.
# emoji_to_role = {
#     discord.PartialEmoji(name='🔴'): 0, # ID of the role associated with unicode emoji '🔴'.
#     discord.PartialEmoji(name='🟡'): 0, # ID of the role associated with unicode emoji '🟡'.
#     discord.PartialEmoji(name='green', id=0): 0, # ID of the role associated with a partial emoji's ID.
# }


# Log readiness.
@goose_bot.event
async def on_ready():
    print('Logged in as ' + goose_bot.user.name)
    print(goose_bot.user.id)
    print('------')


# Roll dice.
@goose_bot.command()
async def roll(ctx, dice: str):
    """Roll dice in NdN format."""
    logging.info("Dice: Rolling dice...")
    try:
        rolls, limit = map(int, dice.split('d'))
    except (Exception,):
        await ctx.send('Format has to be NdN!')
        return
    result = await goose_bot_utils.roll_result(limit, rolls)

    await ctx.send(result)


# List the roles of the server and the command author.
@goose_bot.command()
async def roles(ctx):
    """List available and currently assigned roles."""
    server_roles = ctx.author.guild.roles
    prettified_member_roles = await goose_bot_utils.prettify_roles(ctx.author.roles, "Your roles:")
    prettified_server_roles = await goose_bot_utils.prettify_roles(server_roles, "All roles:")
    logging.info("Role Management: Printing roles for server " + ctx.author.guild.name + ".")
    await ctx.send(prettified_server_roles)
    await ctx.send(prettified_member_roles)


# Add the desired role to the command author or a specific user.
@goose_bot.command()
async def role(ctx, role_name: discord.Role = "", user_name: discord.Member = "author"):
    """Add/remove a role by its name."""
    if role_name == "":
        await ctx.send("Specify a role to add or remove.")
    else:
        try:
            if user_name == "author":
                logging.info("Role Management: Managing role " + role_name.name 
                             + " for " + ctx.author.display_name + ".")
                if role_name in ctx.author.roles:
                    await ctx.author.remove_roles(role_name)
                    await ctx.send("Relieved you of the role `" + role_name.name + "`.")
                else:
                    await ctx.author.add_roles(role_name)
                    await ctx.send("Granted you the role `" + role_name.name + "`.")
            else:
                logging.info("Role Management: Managing role " + role_name.name
                             + " for " + user_name.display_name + ".")
                if role_name in user_name.roles:
                    await user_name.remove_roles(role_name)
                    await ctx.send("Removed `" + role_name.name + "` from " + user_name.display_name + ".")
                else:
                    await user_name.add_roles(role_name)
                    await ctx.send("Granted `" + role_name.name + "` to " + user_name.display_name + ".")
        except (Exception,):
            await ctx.send("Something went wrong assigning roles, sorry!")


# Add a role associated with an appropriate reaction on an appropriate message.
@goose_bot.event
async def on_raw_reaction_add(payload: discord.RawReactionActionEvent):
    if (payload.message_id != int(channel_sub_message_id)) and (payload.message_id != int(notif_sub_message_id)):
        return

    guild = goose_bot.get_guild(payload.guild_id)
    logging.info("Reaction Roles: Reaction added to a subscription message in " + guild.name + "!")
    if guild is None:
        return

    try:
        role_id = await get_role_id_from_emoji(payload.emoji)
    except KeyError:
        logging.info("Reaction Roles: I don't know what role to grant for that emoji.")
        return

    emoji_role = guild.get_role(role_id)
    if emoji_role is None:
        return

    try:
        await payload.member.add_roles(emoji_role)
        logging.info("Reaction Roles: Adding role " + str(emoji_role) + " to " + payload.member.display_name + "!")
        message = await goose_bot.get_channel(
            int(SUB_CHANNEL_ID)).send("Added role `" + str(emoji_role) + "` to " + payload.member.display_name + ".")
        sleep(5)
        await message.delete()
    except discord.HTTPException:
        pass


# Remove a role associated with an appropriate reaction on an appropriate message.
@goose_bot.event
async def on_raw_reaction_remove(payload: discord.RawReactionActionEvent):
    if (payload.message_id != int(channel_sub_message_id)) and (payload.message_id != int(notif_sub_message_id)):
        return

    guild = goose_bot.get_guild(payload.guild_id)
    logging.info("Reaction Roles: Reaction removed from a subscription message in " + guild.name + "!")
    if guild is None:
        return

    try:
        role_id = await get_role_id_from_emoji(payload.emoji)
    except KeyError:
        logging.info("Reaction Roles: I don't know what role to remove for that emoji.")
        return

    emoji_role = guild.get_role(role_id)
    if emoji_role is None:
        return

    member = guild.get_member(payload.user_id)
    if member is None:
        return

    try:
        await member.remove_roles(emoji_role)
        logging.info("Reaction Roles: Removing role " + str(emoji_role) + " from " + member.display_name + "!")
        message = await goose_bot.get_channel(
            int(SUB_CHANNEL_ID)).send("Removed role `" + str(emoji_role) + "` from " + member.display_name + ".")
        sleep(5)
        await message.delete()
    except discord.HTTPException:
        pass


# Refer to the emoji -> role dict in different ways depending on whether a default or custom emoji was provided.
async def get_role_id_from_emoji(emoji):
    if emoji.id is None:
        role_id = emoji_to_role[emoji]
    else:
        role_id = emoji_to_role[emoji.id]
    return role_id


# Send an arbitrary message in an arbitrary channel. Used by daily_message and hourly_message.
async def send_message_in_channel(channel_id, message_str):
    await goose_bot.wait_until_ready()
    channel = goose_bot.get_channel(channel_id)
    logging.info("Sending message " + message_str + " to channel " + channel.name)
    await channel.send(message_str)


# Send a message every day at the defined DAILY_MESSAGE_TIME.
async def daily_message(channel_id, message_str):
    now = datetime.utcnow()
    logging.info("Daily Message: It is now " + str(now) + ".")
    if now.time() > DAILY_MESSAGE_TIME:
        logging.info("Daily Message: The daily message time was " + str(DAILY_MESSAGE_TIME)
                     + " but it is already " + str(now) + ".")
        logging.info("Daily Message: We should wait until tomorrow to send a daily message.")
        tomorrow = datetime.combine(now.date() + timedelta(days=1), time(0))
        logging.info("Daily Message: Tomorrow is " + str(tomorrow) + ".")
        seconds = (tomorrow - now).total_seconds()
        time_str = await goose_bot_utils.make_time_str(seconds)
        logging.info("Daily Message: It will be tomorrow in " + time_str + ".")
        logging.info("Daily Message: Waiting for " + time_str + " (" + str(seconds) + ") seconds...")
        await asyncio.sleep(seconds)
    while True:
        now = datetime.utcnow()
        logging.info("Daily Message: It is now " + str(now) + ".")
        target_time = datetime.combine(now.date(), DAILY_MESSAGE_TIME)
        logging.info("Daily Message: A message should be sent at " + str(target_time) + ".")
        seconds_until_target = (target_time - now).total_seconds()
        time_str = await goose_bot_utils.make_time_str(seconds_until_target)
        logging.info("Daily Message: There are " + time_str + " between now and then.")
        logging.info("Daily Message: Waiting for " + time_str + " (" + str(seconds_until_target) + ") seconds...")
        await asyncio.sleep(seconds_until_target)
        logging.info("Daily Message: Sending daily message!")
        await send_message_in_channel(channel_id, message_str)
        logging.info("Daily Message: Daily message sent.")
        tomorrow = datetime.combine(now.date() + timedelta(days=1), time(0))
        seconds = (tomorrow - now).total_seconds()
        time_str = await goose_bot_utils.make_time_str(seconds)
        logging.info("Daily Message: Tomorrow is " + str(tomorrow) + ", which is in " + time_str + ".")
        logging.info("Daily Message: Waiting for " + str(seconds) + " seconds...")
        await asyncio.sleep(seconds)


# Send a message on the hour, every hour.
async def hourly_message(channel_id, message_str):
    while True:
        now = datetime.utcnow()
        logging.info("Hourly Message: It is now " + str(now) + ".")
        next_hour = now.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
        logging.info("Hourly Message: The next clock hour is " + str(next_hour) + ".")
        seconds_until_next_hour = (next_hour - now).total_seconds()
        time_str = await goose_bot_utils.make_time_str(seconds_until_next_hour)
        logging.info("Hourly Message: There are " + time_str + " between now and then.")
        logging.info("Hourly Message: Waiting for " + time_str + " (" + str(seconds_until_next_hour) + " seconds" + ")...")
        await asyncio.sleep(seconds_until_next_hour)
        logging.info("Hourly Message: Sending hourly message!")
        await send_message_in_channel(channel_id, message_str)
        logging.info("Hourly Message: Hourly message sent.")
        in_an_hour = datetime.utcnow().replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
        logging.info("Hourly Message: An hour from now is " + str(in_an_hour) + ".")
        seconds = (in_an_hour - now).total_seconds()
        time_str = await goose_bot_utils.make_time_str(seconds)
        logging.info("Hourly Message: There are " + time_str + "  between now and then.")
        logging.info("Hourly Message: Waiting for " + time_str + " (" + str(seconds) + ") seconds...")
        await asyncio.sleep(seconds)


# Prepare to maintain daily and hourly message schedules.
def set_up_scheduled_messages():
    goose_bot.loop.create_task(daily_message(DAILY_MESSAGE_CHANNEL_ID, DAILY_MESSAGE))
    goose_bot.loop.create_task(hourly_message(HOURLY_MESSAGE_CHANNEL_ID, HOURLY_MESSAGE))


set_up_scheduled_messages()

# Run the bot!
goose_bot.run(BOT_TOKEN)
