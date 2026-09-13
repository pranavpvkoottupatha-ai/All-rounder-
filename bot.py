import os
import re
import json
import time
import random
from collections import defaultdict, deque

import discord
from discord.ext import commands

# ============================================================
# NOVA - ALL-IN-ONE DISCORD BOT
# ============================================================

TOKEN = os.getenv("DISCORD_TOKEN")

if not TOKEN:
    raise RuntimeError("DISCORD_TOKEN environment variable is missing.")

# -------------------- INTENTS --------------------

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.presences = True

bot = commands.Bot(
    command_prefix="!",
    intents=intents,
    help_command=None
)

# -------------------- DATA --------------------

DATA_FILE = "nova_data.json"

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
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


# -------------------- ANTI-SPAM --------------------

spam_messages = defaultdict(lambda: deque(maxlen=10))
duplicate_messages = defaultdict(lambda: deque(maxlen=5))
user_violations = defaultdict(int)

SPAM_MESSAGE_LIMIT = 6
SPAM_TIME_WINDOW = 7
DUPLICATE_LIMIT = 3
VIOLATION_TIMEOUT = 60

blocked_invite_pattern = re.compile(
    r"(discord\.gg/|discord\.com/invite/)",
    re.IGNORECASE
)

# -------------------- HELPERS --------------------


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
        embed = discord.Embed(
            title=title,
            description=description,
            timestamp=discord.utils.utcnow()
        )
        await channel.send(embed=embed)


async def punish_spammer(message, reason):
    member = message.author

    try:
        await message.delete()
    except discord.HTTPException:
        pass

    user_violations[member.id] += 1

    count = user_violations[member.id]

    if count == 1:
        action = "Warning"
        try:
            await message.channel.send(
                f"⚠️ {member.mention}, please stop spamming.",
                delete_after=5
            )
        except discord.HTTPException:
            pass

    elif count == 2:
        action = "Timeout 1 minute"
        try:
            await member.timeout(
                discord.utils.utcnow() + discord.timedelta(minutes=1),
                reason=reason
            )
        except Exception:
            pass

    elif count >= 3:
        action = "Timeout 5 minutes"
        try:
            await member.timeout(
                discord.utils.utcnow() + discord.timedelta(minutes=5),
                reason=reason
            )
        except Exception:
            pass

    await send_log(
        message.guild,
        "🛡️ Anti-Spam Action",
        f"**User:** {member.mention}\n"
        f"**Reason:** {reason}\n"
        f"**Action:** {action}"
    )


# ============================================================
# EVENTS
# ============================================================

@bot.event
async def on_ready():
    print("================================")
    print(f"Nova is online as {bot.user}")
    print(f"Servers: {len(bot.guilds)}")
    print("================================")

    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} slash commands.")
    except Exception as e:
        print("Slash command sync error:", e)


@bot.event
async def on_member_join(member):
    settings = data["settings"].get(str(member.guild.id), {})
    channel_id = settings.get("welcome_channel")

    if not channel_id:
        return

    channel = member.guild.get_channel(channel_id)

    if channel:
        embed = discord.Embed(
            title="👋 Welcome!",
            description=(
                f"Welcome {member.mention} to **{member.guild.name}**!\n\n"
                "Please read the server rules and enjoy your stay."
            )
        )

        await channel.send(embed=embed)


@bot.event
async def on_member_remove(member):
    settings = data["settings"].get(str(member.guild.id), {})
    channel_id = settings.get("welcome_channel")

    if not channel_id:
        return

    channel = member.guild.get_channel(channel_id)

    if channel:
        await channel.send(
            f"👋 **{member}** has left the server."
        )


@bot.event
async def on_message(message):

    if message.author.bot:
        return

    if not message.guild:
        await bot.process_commands(message)
        return

    # ---------------- ANTI-SPAM ----------------

    now = time.time()
    user_id = message.author.id

    spam_messages[user_id].append(now)

    while (
        spam_messages[user_id]
        and now - spam_messages[user_id][0] > SPAM_TIME_WINDOW
    ):
        spam_messages[user_id].popleft()

    if len(spam_messages[user_id]) >= SPAM_MESSAGE_LIMIT:
        await punish_spammer(message, "Message flood / spam")
        return

    # ---------------- DUPLICATE MESSAGE ----------------

    content = message.content.strip().lower()

    if content:
        duplicate_messages[user_id].append(content)

        if (
            len(duplicate_messages[user_id]) >= DUPLICATE_LIMIT
            and len(set(duplicate_messages[user_id])) == 1
        ):
            await punish_spammer(message, "Repeated duplicate messages")
            duplicate_messages[user_id].clear()
            return

    # ---------------- INVITE SPAM ----------------

    if blocked_invite_pattern.search(message.content):
        if not is_moderator(message.author):
            await punish_spammer(message, "Discord invite spam")
            return

    # ---------------- MASS MENTIONS ----------------

    if len(message.mentions) >= 5:
        if not is_moderator(message.author):
            await punish_spammer(message, "Mass mention spam")
            return

    # ---------------- XP ----------------

    guild_id = str(message.guild.id)
    member_id = str(message.author.id)

    if guild_id not in data["levels"]:
        data["levels"][guild_id] = {}

    if member_id not in data["levels"][guild_id]:
        data["levels"][guild_id] = {
            **data["levels"][guild_id],
            member_id: {
                "xp": 0,
                "level": 1
            }
        }

    user = data["levels"][guild_id][member_id]

    user["xp"] += random.randint(5, 15)

    required_xp = user["level"] * 100

    if user["xp"] >= required_xp:
        user["xp"] -= required_xp
        user["level"] += 1

        try:
            await message.channel.send(
                f"🎉 {message.author.mention} reached **Level "
                f"{user['level']}**!"
            )
        except discord.HTTPException:
            pass

    save_data()

    await bot.process_commands(message)


# ============================================================
# BASIC COMMANDS
# ============================================================

@bot.command()
async def hello(ctx):
    await ctx.send(f"👋 Hi {ctx.author.mention}!")


@bot.command()
async def hi(ctx):
    await ctx.send(f"👋 Hi {ctx.author.mention}!")


@bot.command()
async def ping(ctx):
    latency = round(bot.latency * 1000)
    await ctx.send(f"🏓 Pong! `{latency}ms`")


@bot.command()
async def serverinfo(ctx):
    guild = ctx.guild

    embed = discord.Embed(
        title=f"📊 {guild.name}",
        description="Server information"
    )

    embed.add_field(name="Members", value=str(guild.member_count))
    embed.add_field(name="Channels", value=str(len(guild.channels)))
    embed.add_field(name="Roles", value=str(len(guild.roles)))
    embed.add_field(name="Server ID", value=str(guild.id))

    await ctx.send(embed=embed)


@bot.command()
async def userinfo(ctx, member: discord.Member = None):
    member = member or ctx.author

    embed = discord.Embed(
        title="👤 User Information"
    )

    embed.add_field(name="Username", value=str(member))
    embed.add_field(name="ID", value=str(member.id))
    embed.add_field(name="Joined", value=discord.utils.format_dt(
        member.joined_at, style="R"
    ) if member.joined_at else "Unknown")

    await ctx.send(embed=embed)


# ============================================================
# MODERATION
# ============================================================

@bot.command()
@commands.has_permissions(manage_messages=True)
async def clear(ctx, amount: int = 10):

    if amount < 1 or amount > 100:
        await ctx.send("❌ Choose a number between 1 and 100.")
        return

    deleted = await ctx.channel.purge(limit=amount + 1)

    msg = await ctx.send(
        f"🧹 Deleted **{len(deleted) - 1}** messages."
    )

    await msg.delete(delay=5)


@bot.command()
@commands.has_permissions(moderate_members=True)
async def timeout(ctx, member: discord.Member, minutes: int = 5):

    if member == ctx.author:
        await ctx.send("❌ You cannot timeout yourself.")
        return

    await member.timeout(
        discord.utils.utcnow() + discord.timedelta(minutes=minutes),
        reason=f"By {ctx.author}"
    )

    await ctx.send(
        f"⏳ {member.mention} timed out for **{minutes} minutes**."
    )

    await send_log(
        ctx.guild,
        "⏳ Member Timeout",
        f"{member.mention} was timed out by {ctx.author.mention}."
    )


@bot.command()
@commands.has_permissions(kick_members=True)
async def kick(ctx, member: discord.Member, *, reason="No reason provided"):

    await member.kick(reason=reason)

    await ctx.send(
        f"👢 {member} was kicked.\nReason: `{reason}`"
    )

    await send_log(
        ctx.guild,
        "👢 Member Kicked",
        f"**Member:** {member}\n"
        f"**Moderator:** {ctx.author}\n"
        f"**Reason:** {reason}"
    )


@bot.command()
@commands.has_permissions(ban_members=True)
async def ban(ctx, member: discord.Member, *, reason="No reason provided"):

    await member.ban(reason=reason)

    await ctx.send(
        f"🔨 {member} was banned.\nReason: `{reason}`"
    )

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
async def warn(ctx, member: discord.Member, *, reason="No reason provided"):

    warnings = get_user_warnings(ctx.guild.id, member.id)
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
async def warnings(ctx, member: discord.Member):

    amount = get_user_warnings(
        ctx.guild.id,
        member.id
    )

    await ctx.send(
        f"⚠️ {member.mention} has **{amount} warning(s)**."
    )


@bot.command()
@commands.has_permissions(administrator=True)
async def clearwarnings(ctx, member: discord.Member):

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
async def setlog(ctx, channel: discord.TextChannel = None):

    channel = channel or ctx.channel

    guild_id = str(ctx.guild.id)

    if guild_id not in data["settings"]:
        data["settings"][guild_id] = {}

    data["settings"][guild_id]["log_channel"] = channel.id

    save_data()

    await ctx.send(
        f"✅ Log channel set to {channel.mention}."
    )


@bot.command()
@commands.has_permissions(administrator=True)
async def setwelcome(ctx, channel: discord.TextChannel = None):

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
# LEVEL SYSTEM
# ============================================================

@bot.command()
async def level(ctx, member: discord.Member = None):

    member = member or ctx.author

    guild_id = str(ctx.guild.id)
    member_id = str(member.id)

    user = data["levels"].get(
        guild_id,
        {}
    ).get(
        member_id,
        {"xp": 0, "level": 1}
    )

    await ctx.send(
        f"⭐ {member.mention}\n"
        f"**Level:** {user['level']}\n"
        f"**XP:** {user['xp']}"
    )


# ============================================================
# FUN COMMANDS
# ============================================================

@bot.command()
async def coin(ctx):

    result = random.choice(["Heads", "Tails"])

    await ctx.send(f"🪙 **{result}**!")


@bot.command()
async def dice(ctx):

    result = random.randint(1, 6)

    await ctx.send(f"🎲 You rolled **{result}**!")


@bot.command()
async def choose(ctx, *, options):

    choices = [
        x.strip()
        for x in options.split(",")
        if x.strip()
    ]

    if len(choices) < 2:
        await ctx.send(
            "Example: `!choose pizza, burger, biryani`"
        )
        return

    await ctx.send(
        f"🎯 I choose **{random.choice(choices)}**!"
    )


@bot.command()
async def eightball(ctx, *, question):

    answers = [
        "Yes.",
        "No.",
        "Definitely!",
        "Probably.",
        "Ask again later.",
        "I don't know."
    ]

    await ctx.send(
        f"🎱 **{random.choice(answers)}**"
    )


# ============================================================
# POLL
# ============================================================

@bot.command()
@commands.has_permissions(manage_messages=True)
async def poll(ctx, *, question):

    embed = discord.Embed(
        title="📊 Poll",
        description=question
    )

    message = await ctx.send(embed=embed)

    await message.add_reaction("👍")
    await message.add_reaction("👎")


# ============================================================
# ANNOUNCEMENT
# ============================================================

@bot.command()
@commands.has_permissions(manage_guild=True)
async def announce(ctx, *, text):

    embed = discord.Embed(
        title="📢 Announcement",
        description=text
    )

    embed.set_footer(
        text=f"Announced by {ctx.author}"
    )

    await ctx.send(
        "@everyone",
        embed=embed
    )


# ============================================================
# LOCK / UNLOCK
# ============================================================

@bot.command()
@commands.has_permissions(manage_channels=True)
async def lock(ctx):

    overwrite = ctx.channel.overwrites_for(
        ctx.guild.default_role
    )

    overwrite.send_messages = False

    await ctx.channel.set_permissions(
        ctx.guild.default_role,
        overwrite=overwrite
    )

    await ctx.send("🔒 Channel locked.")


@bot.command()
@commands.has_permissions(manage_channels=True)
async def unlock(ctx):

    overwrite = ctx.channel.overwrites_for(
        ctx.guild.default_role
    )

    overwrite.send_messages = True

    await ctx.channel.set_permissions(
        ctx.guild.default_role,
        overwrite=overwrite
    )

    await ctx.send("🔓 Channel unlocked.")


# ============================================================
# SLOWMODE
# ============================================================

@bot.command()
@commands.has_permissions(manage_channels=True)
async def slowmode(ctx, seconds: int = 0):

    if seconds < 0 or seconds > 21600:
        await ctx.send(
            "❌ Slowmode must be between 0 and 21600 seconds."
        )
        return

    await ctx.channel.edit(
        slowmode_delay=seconds
    )

    if seconds == 0:
        await ctx.send("🐇 Slowmode disabled.")
    else:
        await ctx.send(
            f"🐢 Slowmode set to **{seconds} seconds**."
        )


# ============================================================
# BOT INFO
# ============================================================

@bot.command()
async def botinfo(ctx):

    embed = discord.Embed(
        title="🤖 Nova",
        description="All-in-one Discord server assistant."
    )

    embed.add_field(
        name="🛡️ Security",
        value="Anti-spam, duplicate detection, invite protection"
    )

    embed.add_field(
        name="🔨 Moderation",
        value="Warn, timeout, kick, ban, clear"
    )

    embed.add_field(
        name="👋 Server",
        value="Welcome, logging, announcements"
    )

    embed.add_field(
        name="🎮 Fun",
        value="Coin, dice, choose, 8-ball"
    )

    embed.add_field(
        name="⭐ Levels",
        value="XP and level system"
    )

    await ctx.send(embed=embed)


# ============================================================
# HELP
# ============================================================

@bot.command(name="help")
async def help_command(ctx):

    embed = discord.Embed(
        title="🤖 Nova — Commands",
        description="Use `!command` to run a command."
    )

    embed.add_field(
        name="🛡️ Moderation",
        value=(
            "`!clear 20`\n"
            "`!warn @user reason`\n"
            "`!warnings @user`\n"
            "`!clearwarnings @user`\n"
            "`!timeout @user 5`\n"
            "`!kick @user reason`\n"
            "`!ban @user reason`"
        ),
        inline=False
    )

    embed.add_field(
        name="🔐 Security",
        value=(
            "Anti-spam\n"
            "Duplicate-message detection\n"
            "Invite protection\n"
            "Mass-mention protection"
        ),
        inline=False
    )

    embed.add_field(
        name="👋 Server",
        value=(
            "`!setwelcome #channel`\n"
            "`!setlog #channel`\n"
            "`!announce text`\n"
            "`!lock`\n"
            "`!unlock`\n"
            "`!slowmode 10`"
        ),
        inline=False
    )

    embed.add_field(
        name="🎮 Fun",
        value=(
            "`!coin`\n"
            "`!dice`\n"
            "`!choose a,b,c`\n"
            "`!eightball question`\n"
            "`!poll question`"
        ),
        inline=False
    )

    
