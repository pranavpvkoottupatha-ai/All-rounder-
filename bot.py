import os
import random
import re
import time

from collections import defaultdict, deque
from datetime import timedelta

import discord
from discord.ext import commands


# ============================================================
# CONFIGURATION
# ============================================================

TOKEN = os.getenv("DISCORD_TOKEN")

if not TOKEN:
    raise RuntimeError(
        "DISCORD_TOKEN secret was not found."
    )


# ============================================================
# DISCORD INTENTS
# ============================================================

intents = discord.Intents.default()

intents.message_content = True
intents.members = True


# ============================================================
# COMMAND PREFIX
# ============================================================

def get_prefix(bot, message):
    """
    Supports both:

    hi
    !hi

    ping
    !ping

    etc.
    """

    content = message.content.strip()

    if not content:
        return ["!"]

    first_word = content.split()[0].lower()

    # Remove ! from !command
    command_name = first_word.lstrip("!")

    # If this is an actual bot command,
    # allow both !command and command.
    if bot.get_command(command_name):
        return ["", "!"]

    # Normal messages still require !
    return ["!"]


# ============================================================
# BOT
# ============================================================

bot = commands.Bot(
    command_prefix=get_prefix,
    intents=intents,
    help_command=None
)


# ============================================================
# ANTI-SPAM
# ============================================================

message_history = defaultdict(
    lambda: deque(maxlen=10)
)

# 5 messages in 5 seconds
SPAM_LIMIT = 5
SPAM_TIME = 5

INVITE_PATTERN = re.compile(
    r"(discord\.gg/|discord\.com/invite/)",
    re.IGNORECASE
)


async def punish_spammer(message, reason):

    member = message.author

    if not isinstance(member, discord.Member):
        return

    try:

        # Don't punish administrators
        if member.guild_permissions.administrator:
            return

        # Timeout for 1 minute
        await member.timeout(
            timedelta(minutes=1),
            reason=reason
        )

        await message.channel.send(
            f"⚠️ {member.mention} was timed out for "
            f"1 minute.\n"
            f"**Reason:** {reason}"
        )

    except discord.Forbidden:

        print(
            "❌ Missing permission to timeout member."
        )

    except Exception as error:

        print(
            f"❌ Anti-spam error: {error}"
        )


# ============================================================
# READY EVENT
# ============================================================

@bot.event
async def on_ready():

    print(
        f"Logged in as: {bot.user}"
    )

    print(
        f"Bot ID: {bot.user.id}"
    )

    print(
        f"Servers: {len(bot.guilds)}"
    )

    print(
        "All Rounder is ONLINE!"
    )

    try:

        await bot.change_presence(
            activity=discord.Game(
                name="Type hi or !help"
            )
        )

    except Exception as error:

        print(
            f"Presence error: {error}"
        )


# ============================================================
# MEMBER JOIN
# ============================================================

@bot.event
async def on_member_join(member):

    channel = discord.utils.find(
        lambda c:
            c.name.lower() in [
                "welcome",
                "general",
                "chat"
            ],
        member.guild.text_channels
    )

    if channel:

        try:

            await channel.send(
                f"👋 Welcome {member.mention} "
                f"to **{member.guild.name}**!"
            )

        except discord.Forbidden:

            pass


# ============================================================
# MEMBER LEAVE
# ============================================================

@bot.event
async def on_member_remove(member):

    channel = discord.utils.find(
        lambda c:
            c.name.lower() in [
                "welcome",
                "general",
                "chat"
            ],
        member.guild.text_channels
    )

    if channel:

        try:

            await channel.send(
                f"👋 **{member.name}** has left "
                f"the server."
            )

        except discord.Forbidden:

            pass


# ============================================================
# MESSAGE / ANTI-SPAM SYSTEM
# ============================================================

@bot.event
async def on_message(message):

    # Ignore bots
    if message.author.bot:
        return

    now = time.time()

    user_id = message.author.id

    history = message_history[user_id]

    history.append({
        "time": now,
        "content": message.content
    })

    # Remove messages older than 5 seconds
    while (
        history
        and now - history[0]["time"] > SPAM_TIME
    ):
        history.popleft()


    # --------------------------------------------------------
    # 5 MESSAGES IN 5 SECONDS
    # --------------------------------------------------------

    if len(history) >= SPAM_LIMIT:

        await message.channel.send(
            f"🚨 {message.author.mention} "
            f"**Spam detected!**\n"
            f"Please slow down."
        )

        await punish_spammer(
            message,
            "5 messages sent within 5 seconds."
        )

        history.clear()

        return


    # --------------------------------------------------------
    # REPEATED MESSAGE CHECK
    # --------------------------------------------------------

    recent = [
        item["content"]
        for item in list(history)[-3:]
    ]

    if (
        len(recent) == 3
        and len(set(recent)) == 1
        and recent[0] != ""
    ):

        await message.channel.send(
            f"⚠️ {message.author.mention} "
            f"Repeated messages detected."
        )

        await punish_spammer(
            message,
            "Repeated messages detected."
        )

        history.clear()

        return


    # --------------------------------------------------------
    # DISCORD INVITE CHECK
    # --------------------------------------------------------

    if INVITE_PATTERN.search(
        message.content
    ):

        await message.channel.send(
            f"⚠️ {message.author.mention} "
            f"Discord invite detected."
        )

        await punish_spammer(
            message,
            "Discord invite detected."
        )

        return


    # --------------------------------------------------------
    # MASS MENTION CHECK
    # --------------------------------------------------------

    if len(message.mentions) >= 5:

        await message.channel.send(
            f"⚠️ {message.author.mention} "
            f"Mass mentions detected."
        )

        await punish_spammer(
            message,
            "Mass mentions detected."
        )

        return


    # IMPORTANT:
    # This allows the commands to work.
    await bot.process_commands(message)


# ============================================================
# BASIC COMMANDS
# ============================================================

@bot.command()
async def hi(ctx):

    await ctx.send(
        f"👋 Hi {ctx.author.mention}!"
    )


@bot.command()
async def hello(ctx):

    await ctx.send(
        f"👋 Hello {ctx.author.mention}!"
    )


@bot.command()
async def ping(ctx):

    latency = round(
        bot.latency * 1000
    )

    await ctx.send(
        f"🏓 Pong! `{latency}ms`"
    )


# ============================================================
# SERVER INFO
# ============================================================

@bot.command()
async def serverinfo(ctx):

    guild = ctx.guild

    embed = discord.Embed(
        title="🌐 Server Information",
        color=discord.Color.blue()
    )

    embed.add_field(
        name="Server",
        value=guild.name,
        inline=False
    )

    embed.add_field(
        name="Members",
        value=guild.member_count,
        inline=True
    )

    embed.add_field(
        name="Channels",
        value=len(guild.channels),
        inline=True
    )

    embed.add_field(
        name="Roles",
        value=len(guild.roles),
        inline=True
    )

    await ctx.send(
        embed=embed
    )


# ============================================================
# USER INFO
# ============================================================

@bot.command()
async def userinfo(ctx, member: discord.Member = None):

    member = member or ctx.author

    embed = discord.Embed(
        title="👤 User Information",
        color=discord.Color.green()
    )

    embed.add_field(
        name="Username",
        value=str(member),
        inline=False
    )

    embed.add_field(
        name="ID",
        value=member.id,
        inline=False
    )

    embed.add_field(
        name="Joined Server",
        value=(
            member.joined_at.strftime(
                "%d %B %Y"
            )
            if member.joined_at
            else "Unknown"
        ),
        inline=False
    )

    await ctx.send(
        embed=embed
    )


# ============================================================
# CLEAR
# ============================================================

@bot.command()
@commands.has_permissions(
    manage_messages=True
)
async def clear(ctx, amount: int = 10):

    if amount < 1:
        await ctx.send(
            "❌ Amount must be at least 1."
        )
        return

    if amount > 100:
        amount = 100

    deleted = await ctx.channel.purge(
        limit=amount + 1
    )

    msg = await ctx.send(
        f"🧹 Deleted {len(deleted) - 1} messages."
    )

    await msg.delete(
        delay=5
    )


# ============================================================
# TIMEOUT
# ============================================================

@bot.command()
@commands.has_permissions(
    moderate_members=True
)
async def timeout(
    ctx,
    member: discord.Member,
    minutes: int = 1
):

    if minutes < 1:
        minutes = 1

    if minutes > 10080:
        minutes = 10080

    await member.timeout(
        timedelta(minutes=minutes),
        reason=f"Timeout by {ctx.author}"
    )

    await ctx.send(
        f"🔇 {member.mention} was timed out "
        f"for {minutes} minute(s)."
    )


# ============================================================
# K
