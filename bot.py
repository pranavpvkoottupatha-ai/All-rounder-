import os
import re
import json
import time
import random
from datetime import timedelta
from collections import defaultdict, deque

import discord
from discord.ext import commands

# ============================================================
# ALL ROUNDER - ALL-IN-ONE DISCORD BOT
# ============================================================

TOKEN = os.getenv("DISCORD_TOKEN")

if not TOKEN:
    raise RuntimeError("DISCORD_TOKEN environment variable is missing.")

# ============================================================
# INTENTS
# ============================================================

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(
    command_prefix="!",
    intents=intents,
    help_command=None
)

# ============================================================
# DATA
# ============================================================

DATA_FILE = "all_rounder_data.json"

DEFAULT_DATA = {
    "warnings": {},
    "levels": {},
    "settings": {}
}

try:
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
except (FileNotFoundError, json.JSONDecodeError):
    data = DEFAULT_DATA


def save_data():
    try:
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        print("Data save error:", e)


# ============================================================
# ANTI-SPAM
# ============================================================

spam_messages = defaultdict(lambda: deque(maxlen=10))
duplicate_messages = defaultdict(lambda: deque(maxlen=5))
user_violations = defaultdict(int)

SPAM_MESSAGE_LIMIT = 6
SPAM_TIME_WINDOW = 7
DUPLICATE_LIMIT = 3

blocked_invite_pattern = re.compile(
    r"(discord\.gg/|discord\.com/invite/)",
    re.IGNORECASE
)


# ============================================================
# HELPERS
# ============================================================

def is_moderator(member):
    return (
        member.guild_permissions.manage_messages
        or member.guild_permissions.moderate_members
        or member.guild_permissions.administrator
    )


def get_user_warnings(guild_id, user_id):
    guild_id = str(guild_id)
    user_id = str(user_id)

    if guild_id not in data["warnings"]:
        data["warnings"][guild_id] = {}

    if user_id not in data["warnings"][guild_id]:
        data["warnings"][guild_id][user_id] = 0

    return data["warnings"][guild_id][user_id]


def set_user_warnings(guild_id, user_id, amount):
    guild_id = str(guild_id)
    user_id = str(user_id)

    if guild_id not in data["warnings"]:
        data["warnings"][guild_id] = {}

    data["warnings"][guild_id][user_id] = amount
    save_data()


async def send_log(guild, title, description):
    settings = data["settings"].get(str(guild.id), {})
    channel_id = settings.get("log_channel")

    if not channel_id:
        return

    channel = guild.get_channel(channel_id)

    if channel:
        try:
            embed = discord.Embed(
                title=title,
                description=description,
                timestamp=discord.utils.utcnow()
            )

            await channel.send(embed=embed)

        except discord.HTTPException:
            pass


# ============================================================
# SPAM PUNISHMENT
# ============================================================

async def punish_spammer(message, reason):

    member = message.author

    # Delete spam message
    try:
        await message.delete()
    except discord.HTTPException:
        pass

    user_violations[member.id] += 1

    count = user_violations[member.id]

    # First violation = warning
    if count == 1:

        action = "Warning"

        try:
            await message.channel.send(
                f"⚠️ {member.mention}, please stop spamming.",
                delete_after=5
            )
        except discord.HTTPException:
            pass

    # Second violation = 1 minute timeout
    elif count == 2:

        action = "Timeout 1 minute"

        try:
            await member.timeout(
                timedelta(minutes=1),
                reason=reason
            )
        except discord.HTTPException:
            pass
        except discord.Forbidden:
            pass

    # Third+ violation = 5 minute timeout
    else:

        action = "Timeout 5 minutes"

        try:
            await member.timeout(
                timedelta(minutes=5),
                reason=reason
            )
        except discord.HTTPException:
            pass
        except discord.Forbidden:
            pass

    await send_log(
        message.guild,
        "🛡️ Anti-Spam Action",
        f"**User:** {member.mention}\n"
        f"**Reason:** {reason}\n"
        f"**Action:** {action}"
    )


# ============================================================
# READY EVENT
# ============================================================

@bot.event
async def on_ready():

    print("====================================")
    print(f"🤖 All Rounder is online as {bot.user}")
    print(f"🆔 Bot ID: {bot.user.id}")
    print(f"🌐 Servers: {len(bot.guilds)}")
    print("====================================")

    try:
        synced = await bot.tree.sync()
        print(f"Slash commands synced: {len(synced)}")
    except Exception as e:
        print("Slash command sync error:", e)


# ============================================================
# MEMBER JOIN
# ============================================================

@bot.event
async def on_member_join(member):

    settings = data["settings"].get(
        str(member.guild.id),
        {}
    )

    channel_id = settings.get("welcome_channel")

    if not channel_id:
        return

    channel = member.guild.get_channel(channel_id)

    if channel:

        try:
            embed = discord.Embed(
                title="👋 Welcome!",
                description=(
                    f"Welcome {member.mention} to "
                    f"**{member.guild.name}**!\n\n"
                    "Please read the server rules and enjoy your stay."
                )
            )

            await channel.send(embed=embed)

        except discord.HTTPException:
            pass


# ============================================================
# MEMBER LEAVE
# ============================================================

@bot.event
async def on_member_remove(member):

    settings = data["settings"].get(
        str(member.guild.id),
        {}
    )

    channel_id = settings.get("welcome_channel")

    if not channel_id:
        return

    channel = member.guild.get_channel(channel_id)

    if channel:

        try:
            await channel.send(
                f"👋 **{member}** has left the server."
            )
        except discord.HTTPException:
            pass


# ============================================================
# MESSAGE EVENT
# ============================================================

@bot.event
async def on_message(message):

    # Ignore bots
    if message.author.bot:
        return

    # Ignore DMs for anti-spam
    if not message.guild:
        await bot.process_commands(message)
        return

    user_id = message.author.id
    now = time.time()

    # ========================================================
    # ANTI-SPAM FLOOD
    # ========================================================

    spam_messages[user_id].append(now)

    while (
        spam_messages[user_id]
        and now - spam_messages[user_id][0] > SPAM_TIME_WINDOW
    ):
        spam_messages[user_id].popleft()

    if (
        len(spam_messages[user_id]) >= SPAM_MESSAGE_LIMIT
        and not is_moderator(message.author)
    ):
        await punish_spammer(
            message,
            "Message flood / spam"
        )
        return

    # ========================================================
    # DUPLICATE MESSAGE DETECTION
    # ========================================================

    content = message.content.strip().lower()

    if content:

        duplicate_messages[user_id].append(content)

        if (
            len(duplicate_messages[user_id]) >= DUPLICATE_LIMIT
            and len(set(duplicate_messages[user_id])) == 1
            and not is_moderator(message.author)
        ):

            await punish_spammer(
                message,
                "Repeated duplicate messages"
            )

            duplicate_messages[user_id].clear()
            return

    # ========================================================
    # DISCORD INVITE PROTECTION
    # ========================================================

    if blocked_invite_pattern.search(message.content):

        if not is_moderator(message.author):

            await punish_spammer(
                message,
                "Discord invite spam"
            )

            return

    # ========================================================
    # MASS MENTION PROTECTION
    # ========================================================

    if len(message.mentions) >= 5:

        if not is_moderator(message.author):

            await punish_spammer(
                message,
                "Mass mention spam"
            )

            return

    # ========================================================
    # XP SYSTEM
    # ========================================================

    guild_id = str(message.guild.id)
    member_id = str(message.author.id)

    if guild_id not in data["levels"]:
        data["levels"][guild_id] = {}

    if member_id not in data["levels"][guild_id]:

        data["levels"][guild_id][member_id] = {
            "xp": 0,
            "level": 1
        }

    user = data["levels"][guild_id][member_id]

    user["xp"] += random.randint(5, 15)

    required_xp = user["level"] * 100

    if user["xp"] >= required_xp:

        user["xp"] -= required_xp
        user["level"] += 1

        try:
            await message.channel.send(
                f"🎉 {message.author.mention} reached "
                f"**Level {user['level']}**!"
            )
        except discord.HTTPException:
            pass

    save_data()

    # ========================================================
    # PROCESS COMMANDS
    # ========================================================

    await bot.process_commands(message)


# ============================================================
# BASIC COMMANDS
# ============================================================

@bot.command()
async def hello(ctx):

    await ctx.send(
        f"👋 Hi {ctx.author.mention}! "
        f"I'm **All Rounder**."
    )


@bot.command()
async def hi(ctx):

    await ctx.send(
        f"👋 Hi {ctx.author.mention}!"
    )


@bot.command()
async def ping(ctx):

    latency = round(bot.latency * 1000)

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
        title=f"📊 {guild.name}",
        description="Server information"
    )

    embed.add_field(
        name="Members",
        value=str(guild.member_count)
    )

    embed.add_field(
        name="Channels",
        value=str(len(guild.channels))
    )

    embed.add_field(
        name="Roles",
        value=str(len(guild.roles))
    )

    embed.add_field(
        name="Server ID",
        value=str(guild.id)
    )

    await ctx.send(embed=embed)


# ============================================================
# USER INFO
# ============================================================

@bot.command()
async def userinfo(ctx, member: discord.Member = None):

    member = member or ctx.author

    embed = discord.Embed(
        title="👤 User Information"
    )

    embed.add_field(
        name="Username",
        value=str(member)
    )

    embed.add_field(
        name="ID",
        value=str(member.id)
    )

    joined = (
        discord.utils.format_dt(
            member.joined_at,
            style="R"
        )
        if member.joined_at
        else "Unknown"
    )

    embed.add_field(
        name="Joined",
        value=joined
    )

    await ctx.send(embed=embed)


# ============================================================
# CLEAR
# ============================================================

@bot.command()
@commands.has_permissions(manage_messages=True)
async def clear(ctx, amount: int = 10):

    if amount < 1 or amount > 100:

        await ctx.send(
            "❌ Choose a number between 1 and 100."
        )

        return

    deleted = await ctx.channel.purge(
        limit=amount + 1
    )

    msg = await ctx.send(
        f"🧹 Deleted **{len(deleted) - 1}** messages."
    )

    await msg.delete(delay=5)


# ============================================================
# TIMEOUT
# ============================================================

@bot.command()
@commands.has_permissions(moderate_members=True)
async def timeout(
    ctx,
    member: discord.Member,
    minutes: int = 5
):

    if member == ctx.author:

        await ctx.send(
            "❌ You cannot timeout yourself."
        )

        return

    if minutes < 1 or minutes > 40320:

        await ctx.send(
            "❌ Timeout must be between 1 and 40320 minutes."
        )

        return

    try:

        await member.timeout(
            timedelta(minutes=minutes),
            reason=f"By {ctx.author}"
        )

        await ctx.send(
            f"⏳ {member.mention} timed out for "
            f"**{minutes} minutes**."
        )

    except discord.Forbidden:

        await ctx.send(
            "❌ I don't have permission to timeout that member."
        )

        return

    await send_log(
        ctx.guild,
        "⏳ Member Timeout",
        f"{member.mention} was timed out by "
        f"{ctx.author.mention}."
    )


# ============================================================
# KICK
# ============================================================

@bot.command()
@commands.has_permissions(kick_members=True)
async def kick(
    ctx,
    member: discord.Member,
    *,
    reason="No reason provided"
):

    try:

        await member.kick(reason=reason)

        await ctx.send(
            f"👢 {member} was kicked.\n"
            f"Reason: `{reason}`"
        )

    except discord.Forbidden:

        await ctx.send(
            "❌ I don't have permission to kick that member."
        )

        return

    await send_log(
        ctx.guild,
        "👢 Member Kicked",
        f"**Member:** {member}\n"
        f"**Moderator:** {ctx.author}\n"
        f"**Reason:** {reason}"
    )


# ============================================================
# BAN
# ============================================================

@bot.command()
@commands.has_permissions(ban_members=True)
async def ban(
    ctx,
    member: discord.Member,
    *,
    reason="No reason provided"
):

    try:

        await member.ban(reason=reason)

        await ctx.send(
            f"🔨 {member} was banned.\n"
            f"Reason: `{reason}`"
        )

    except discord.Forbidden:

        await ctx.send(
            "❌ I don't have permission to ban that member."
        )

        return

    await send_log(
        ctx.guild,
        "🔨 Member Banned",
        f"**Member:** {member}\n"
        f"**Moderator:** {ctx.author}\n"
        f"**Reason:** {reason}"
    )


# ============================================================
# WARNING SYSTEM
# ============================================================

@bot.command()
@commands.has_permissions(manage_messages=True)
async def warn(
    ctx,
    member: discord.Member,
    *,
    reason="No reason provided"
):

    warnings = get_user_warnings(
        ctx.guild.id,
        member.id
    )

    warnings += 1

    set_user_warnings(
        ctx.guild.id,
        member.id,
        warnings
    )

    await ctx.send(
        f"⚠️ {member.mention} has been warned.\n"
        f"**Warnings:** {warnings}\n"
        f"**Reason:** {reason}"
    )

    await send_log(
        ctx.guild,
        "⚠️ Warning",
        f"**Member:** {member.mention}\n"
        f"**Moderator:** {ctx.author.mention}\n"
        f"**Warnings:** {warnings}\n"
        f"**Reason:** {reason}"
    )


@bot.command()
@commands.has_permissions(manage_messages=True)
async def warnings(
    ctx,
    member: discord.Member
):

    amount = get_user_warnings(
        ctx.guild.id,
        member.id
    )

    await ctx.send(
        f"⚠️ {member.mention} has "
        f"**{amount} warning(s)**."
    )


@bot.command()
@commands.has_permissions(administrator=True)
async def clearwarnings(
    ctx,
    member: discord.Member
):

    set_user_warnings(
        ctx.guild.id,
        member.id,
        0
    )

    await ctx.send(
        f"✅ Cleared warnings for {member.mention}."
    )


# ============================================================
# LOGGING
# ============================================================

@bot.command()
@commands.has_permissions(administrator=True)
async def setlog(
    ctx,
    channel: discord.TextChannel = None
):

    channel = channel or ctx.channel

    guild_id = str(ctx.guild.id)

    if guild_id not in data["settings"]:
        data["settings"][guild_id] = {}

    data["settings"][guild_id]["log_channel"] = channel.id

    save_data()

    await ctx.send(
        f"✅ Log channel set to {channel.mention}."
    )


# ============================================================
# WELCOME
# ============================================================

@bot.command()
@commands.has_permissions(administrator=True)
async def setwelcome(
    ctx,
    channel: discord.TextChannel = None
):

    channel = channel or ctx.channel

    guild_id = str(ctx.guild.id)

    if guild_id not in data["settings"]:
        data["settings"][guild_id] = {}

    data["settings"][guild_id]["welcome_channel"] = channel.id

    save_data()

    await ctx.send(
        f"✅ Welcome channel set to {channel.mention}."
    )


# ============================================================
# LEVEL
# ============================================================

@bot.command()
async def level(
    ctx,
    member: discord.Member = None
):

    member = member or ctx.author

    guild_id = str(ctx.guild.id)
    member_id = str(member.id)

    user = data["levels"].get(
        guild_id,
        {}
    ).get(
        member_id,
        {
            "xp": 0,
            "level": 1
        }
    )

    await ctx.send(
        f"⭐ {member.mention}\n"
        f"**Level:** {user['level']}\n"
        f"**XP:** {user['xp']}"
    )


# ============================================================
# COIN
# ============================================================

@bot.command()
async def coin(ctx):

    result = random.choice(
        ["Heads", "Tails"]
    )

