# Goose Bot Discord management tool meant for use by regular server members.
# Made by Gaelan O'Shea-McKay for personal non-commercial use.

# Import discord packages
import discord
from discord.ext import commands

# Import env file packages
import os
from dotenv import load_dotenv

# Import utils for the bot
import goose_bot_utils
import extended_emoji_dict

# Import time for some delays
from time import sleep

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


# Set up required intents
intents = discord.Intents.default()
intents.typing = False
intents.presences = False
intents.members = True

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
    print("Rolling dice...")
    """Roll dice in NdN format."""
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
    server_roles = ctx.author.guild.roles
    prettified_member_roles = await goose_bot_utils.prettify_roles(ctx.author.roles, "Your roles:")
    prettified_server_roles = await goose_bot_utils.prettify_roles(server_roles, "All roles:")
    await ctx.send(prettified_server_roles)
    await ctx.send(prettified_member_roles)


# Add the desired role to the command author or a specific user.
@goose_bot.command()
async def role(ctx, role_name: discord.Role = "", user_name: discord.Member = "author"):
    if role_name == "":
        await ctx.send("Specify a role to add or remove.")
    else:
        try:
            if user_name == "author":
                print("Managing role " + role_name.name + " for " + ctx.author.display_name + ".")
                if role_name in ctx.author.roles:
                    await ctx.author.remove_roles(role_name)
                    await ctx.send("Relieved you of the role `" + role_name.name + "`.")
                else:
                    await ctx.author.add_roles(role_name)
                    await ctx.send("Granted you the role `" + role_name.name + "`.")
            else:
                print("Managing role " + role_name.name + " for " + user_name.display_name + ".")
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
    print("Reaction added to a subscription message in " + guild.name + "!")
    if guild is None:
        return

    try:
        role_id = await get_role_id_from_emoji(payload.emoji)
    except KeyError:
        print("I don't know what role to grant for that emoji.")
        return

    emoji_role = guild.get_role(role_id)
    if emoji_role is None:
        return

    try:
        await payload.member.add_roles(emoji_role)
        print("Adding role " + str(emoji_role) + " to " + payload.member.display_name + "!")
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
    print("Reaction removed from a subscription message in " + guild.name + "!")
    if guild is None:
        return

    try:
        role_id = await get_role_id_from_emoji(payload.emoji)
    except KeyError:
        print("I don't know what role to remove for that emoji.")
        return

    emoji_role = guild.get_role(role_id)
    if emoji_role is None:
        return

    member = guild.get_member(payload.user_id)
    if member is None:
        return

    try:
        await member.remove_roles(emoji_role)
        print("Removing role " + str(emoji_role) + " from " + member.display_name + "!")
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


# Run the bot!
goose_bot.run(BOT_TOKEN)
