import os
import re
import json
import time
import random
from datetime import timedelta
from collections import defaultdict, deque

import discord
from discord.ext import commands


# =========================================================
# TOKEN
# =========================================================

TOKEN = os.getenv("DISCORD_TOKEN")

if not TOKEN:
    raise RuntimeError("DISCORD_TOKEN is not set in GitHub Secrets.")


# =========================================================
# INTENTS
# =========================================================

intents = discord.Intents.default()
intents.message_content = True
intents.members = True


# =========================================================
# BOT
# =========================================================

bot = commands.Bot(
    command_prefix="!",
    intents=intents,
    help_command=None
)


# =========================================================
# DATA
# =========================================================

DATA_FILE = "all_rounder_data.json"

default_data = {
    "warnings": {},
    "levels": {},
    "settings": {}
}


def load_data():
    if not os.path.exists(DATA_FILE):
        return default_data.copy()

    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default_data.copy()


data = load_data()


def save_data():
    try:
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        print(f"Data save error: {e}")


# =========================================================
# ANTI-SPAM
# =========================================================

message_history = defaultdict(lambda: deque(maxlen=10))

SPAM_LIMIT = 6
SPAM_TIME = 7

INVITE_PATTERN = re.compile(
    r"(discord\.gg/|discord\.com/invite/)",
    re.IGNORECASE
)


async def punish_spammer(message, reason):
    member = message.author

    try:
        user_id = str(member.id)

        if user_id not in data["warnings"]:
            data["warnings"][user_id] = 0

        data["warnings"][user_id] += 1
        warning_count = data["warnings"][user_id]

        save_data()

        if warning_count == 1:
            await message.channel.send(
                f"⚠️ {member.mention}, warning 1/3: {reason}"
            )

        elif warning_count == 2:
            await member.timeout(
                timedelta(minutes=1),
                reason=reason
            )

            await message.channel.send(
                f"⏱️ {member.mention} has been timed out for 1 minute."
            )

        else:
            await member.timeout(
                timedelta(minutes=5),
                reason=reason
            )

            await message.channel.send(
                f"⏱️ {member.mention} has been timed out for 5 minutes."
            )

    except discord.Forbidden:
        print("I don't have permission to punish this member.")

    except Exception as e:
        print(f"Anti-spam error: {e}")


# =========================================================
# READY
# =========================================================

@bot.event
async def on_ready():
    print("===================================")
    print(f"Logged in as: {bot.user}")
    print(f"Bot ID: {bot.user.id}")
    print(f"Servers: {len(bot.guilds)}")
    print("All Rounder is ONLINE!")
    print("===================================")

    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} slash commands.")
    except Exception as e:
        print(f"Slash command sync error: {e}")


# =========================================================
# MEMBER JOIN
# =========================================================

@bot.event
async def on_member_join(member):
    guild_id = str(member.guild.id)

    channel_id = data["settings"].get(guild_id, {}).get("welcome_channel")

    if channel_id:
        channel = member.guild.get_channel(int(channel_id))

        if channel:
            await channel.send(
                f"👋 Welcome {member.mention} to **{member.guild.name}**!"
            )


# =========================================================
# MEMBER LEAVE
# =========================================================

@bot.event
async def on_member_remove(member):
    guild_id = str(member.guild.id)

    channel_id = data["settings"].get(guild_id, {}).get("welcome_channel")

    if channel_id:
        channel = member.guild.get_channel(int(channel_id))

        if channel:
            await channel.send(
                f"👋 **{member.name}** has left the server."
            )


# =========================================================
# MESSAGE EVENT
# =========================================================

@bot.event
async def on_message(message):

    if message.author.bot:
        return

    now = time.time()
    user_id = message.author.id

    history = message_history[user_id]

    history.append({
        "time": now,
        "content": message.content
    })

    # Remove old messages
    while history and now - history[0]["time"] > SPAM_TIME:
        history.popleft()

    # Too many messages
    if len(history) >= SPAM_LIMIT:
        await punish_spammer(
            message,
            "Too many messages in a short time."
        )
        history.clear()
        return

    # Duplicate messages
    recent_contents = [
        item["content"]
        for item in list(history)[-3:]
    ]

    if len(recent_contents) == 3 and len(set(recent_contents)) == 1:
        await punish_spammer(
            message,
            "Repeated messages detected."
        )
        history.clear()
        return

    # Discord invite
    if INVITE_PATTERN.search(message.content):
        await punish_spammer(
            message,
            "Discord invite detected."
        )

    # Mass mentions
    if len(message.mentions) >= 5:
        await punish_spammer(
            message,
            "Mass mentions detected."
        )

    # XP
    guild_id = str(message.guild.id) if message.guild else None

    if guild_id:
        user_key = f"{guild_id}:{message.author.id}"

        if user_key not in data["levels"]:
            data["levels"][user_key] = {
                "xp": 0,
                "level": 1
            }

        profile = data["levels"][user_key]

        profile["xp"] += random.randint(1, 5)

        required_xp = profile["level"] * 100

        if profile["xp"] >= required_xp:
            profile["xp"] -= required_xp
            profile["level"] += 1

            try:
                await message.channel.send(
                    f"🎉 {message.author.mention} reached "
                    f"**Level {profile['level']}**!"
                )
            except Exception:
                pass

        # Don't save every single message
        if random.randint(1, 20) == 1:
            save_data()

    await bot.process_commands(message)


# =========================================================
# BASIC COMMANDS
# =========================================================

@bot.command(name="hello")
async def hello(ctx):
    await ctx.send(
        f"👋 Hello {ctx.author.mention}! I'm **All Rounder**."
    )


@bot.command(name="hi")
async def hi(ctx):
    await ctx.send(
        f"👋 Hi {ctx.author.mention}!"
    )


@bot.command(name="ping")
async def ping(ctx):
    latency = round(bot.latency * 1000)

    await ctx.send(
        f"🏓 Pong! **{latency}ms**"
    )


# =========================================================
# SERVER INFO
# =========================================================

@bot.command(name="serverinfo")
async def serverinfo(ctx):

    guild = ctx.guild

    embed = discord.Embed(
        title="📊 Server Information",
        description=guild.name
    )

    embed.add_field(
        name="👥 Members",
        value=str(guild.member_count)
    )

    embed.add_field(
        name="🆔 Server ID",
        value=str(guild.id)
    )

    embed.add_field(
        name="📅 Created",
        value=guild.created_at.strftime("%d-%m-%Y")
    )

    await ctx.send(embed=embed)


# =========================================================
# USER INFO
# =========================================================

@bot.command(name="userinfo")
async def userinfo(ctx, member: discord.Member = None):

    member = member or ctx.author

    embed = discord.Embed(
        title="👤 User Information"
    )

    embed.add_field(
        name="Name",
        value=str(member)
    )

    embed.add_field(
        name="ID",
        value=str(member.id)
    )

    embed.add_field(
        name="Joined Server",
        value=member.joined_at.strftime("%d-%m-%Y")
        if member.joined_at else "Unknown"
    )

    await ctx.send(embed=embed)


# =========================================================
# CLEAR
# =========================================================

@bot.command(name="clear")
@commands.has_permissions(manage_messages=True)
async def clear(ctx, amount: int = 10):

    if amount < 1:
        await ctx.send("❌ Amount must be at least 1.")
        return

    if amount > 100:
        amount = 100

    deleted = await ctx.channel.purge(limit=amount + 1)

    msg = await ctx.send(
        f"🧹 Deleted **{len(deleted) - 1}** messages."
    )

    await msg.delete(delay=3)


# =========================================================
# TIMEOUT
# =========================================================

@bot.command(name="timeout")
@commands.has_permissions(moderate_members=True)
async def timeout(
    ctx,
    member: discord.Member,
    minutes: int = 5,
    *,
    reason="No reason provided"
):

    if minutes < 1:
        minutes = 1

    if minutes > 40320:
        minutes = 40320

    await member.timeout(
        timedelta(minutes=minutes),
        reason=reason
    )

    await ctx.send(
        f"⏱️ {member.mention} timed out for "
        f"**{minutes} minutes**.\nReason: {reason}"
    )


# =========================================================
# KICK
# =========================================================

@bot.command(name="kick")
@commands.has_permissions(kick_members=True)
async def kick(
    ctx,
    member: discord.Member,
    *,
    reason="No reason provided"
):

    await member.kick(reason=reason)

    await ctx.send(
        f"👢 **{member}** was kicked.\nReason: {reason}"
    )


# =========================================================
# BAN
# =========================================================

@bot.command(name="ban")
@commands.has_permissions(ban_members=True)
async def ban(
    ctx,
    member: discord.Member,
    *,
    reason="No reason provided"
):

    await member.ban(reason=reason)

    await ctx.send(
        f"🔨 **{member}** was banned.\nReason: {reason}"
    )


# =========================================================
# WARN
# =========================================================

@bot.command(name="warn")
@commands.has_permissions(moderate_members=True)
async def warn(
    ctx,
    member: discord.Member,
    *,
    reason="No reason provided"
):

    user_id = str(member.id)

    if user_id not in data["warnings"]:
        data["warnings"][user_id] = 0

    data["warnings"][user_id] += 1

    save_data()

    await ctx.send(
        f"⚠️ {member.mention} has been warned.\n"
        f"Warnings: **{data['warnings'][user_id]}**\n"
        f"Reason: {reason}"
    )


# =========================================================
# WARNINGS
# =========================================================

@bot.command(name="warnings")
async def warnings(ctx, member: discord.Member = None):

    member = member or ctx.author

    count = data["warnings"].get(
        str(member.id),
        0
    )

    await ctx.send(
        f"⚠️ **{member}** has **{count}** warning(s)."
    )


# =========================================================
# SET LOG CHANNEL
# =========================================================

@bot.command(name="setlog")
@commands.has_permissions(manage_guild=True)
async def setlog(ctx):

    guild_id = str(ctx.guild.id)

    if guild_id not in data["settings"]:
        data["settings"][guild_id] = {}

    data["settings"][guild_id]["log_channel"] = ctx.channel.id

    save_data()

    await ctx.send(
        f"✅ Log channel set to {ctx.channel.mention}"
    )


# =========================================================
# SET WELCOME CHANNEL
# =========================================================

@bot.command(name="setwelcome")
@commands.has_permissions(manage_guild=True)
async def setwelcome(ctx):

    guild_id = str(ctx.guild.id)

    if guild_id not in data["settings"]:
        data["settings"][guild_id] = {}

    data["settings"][guild_id]["welcome_channel"] = ctx.channel.id

    save_data()

    await ctx.send(
        f"✅ Welcome/leave channel set to {ctx.channel.mention}"
    )


# =========================================================
# LEVEL
# =========================================================

@bot.command(name="level")
async def level(ctx, member: discord.Member = None):

    member = member or ctx.author

    guild_id = str(ctx.guild.id)
    user_key = f"{guild_id}:{member.id}"

    profile = data["levels"].get(
        user_key,
        {
            "xp": 0,
            "level": 1
        }
    )

    await ctx.send(
        f"⭐ **{member.display_name}**\n"
        f"Level: **{profile['level']}**\n"
        f"XP: **{profile['xp']}**"
    )


# =========================================================
# COIN
# =========================================================

@bot.command(name="coin")
async def coin(ctx):

    result = random.choice(
        ["Heads 🪙", "Tails 🪙"]
    )

    await ctx.send(
        f"🪙 **{result}**"
    )


# =========================================================
# DICE
# =========================================================

@bot.command(name="dice")
async def dice(ctx):

    number = random.randint(1, 6)

    await ctx.send(
        f"🎲 You rolled **{number}**!"
    )


# =========================================================
# CHOOSE
# =========================================================

@bot.command(name="choose")
async def choose(ctx, *choices):

    if len(choices) < 2:
        await ctx.send(
            "❌ Give me at least two choices.\n"
            "Example: `!choose pizza burger`"
        )
        return

    result = random.choice(choices)

    await ctx.send(
        f"🎯 I choose: **{result}**"
    )


# =========================================================
# EIGHT BALL
# =========================================================

@bot.command(name="eightball")
async def eightball(ctx, *, question=""):

    answers = [
        "Yes 👍",
        "No 👎",
        "Maybe 🤔",
        "Definitely! ✅",
        "Ask again later 🔮",
        "I don't know 😅"
    ]

    if not question:
        await ctx.send(
            "🔮 Ask me a question!"
        )
        return

    await ctx.send(
        f"🔮 **{random.choice(answers)}**"
    )


# =========================================================
# POLL
# =========================================================

@bot.command(name="poll")
async def poll(ctx, *, question):

    embed = discord.Embed(
        title="📊 Poll",
        description=question
    )

    msg = await ctx.send(embed=embed)

    await msg.add_reaction("👍")
    await msg.add_reaction("👎")


# =========================================================
# ANNOUNCE
# =========================================================

@bot.command(name="announce")
@commands.has_permissions(manage_guild=True)
async def announce(ctx, *, message):

    embed = discord.Embed(
        title="📢 Announcement",
        description=message
    )

    await ctx.send(
        content="@everyone",
        embed=embed,
        allowed_mentions=discord.AllowedMentions(
            everyone=True
        )
    )


# =========================================================
# LOCK
# =========================================================

@bot.command(name="lock")
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


# =========================================================
# UNLOCK
# =========================================================

@bot.command(name="unlock")
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


# =========================================================
# SLOWMODE
# =========================================================

@bot.command(name="slowmode")
@commands.has_permissions(manage_channels=True)
async def slowmode(ctx, seconds: int = 0):

    if seconds < 0:
        seconds = 0

    if seconds > 21600:
        seconds = 21600

    await ctx.channel.edit(
        slowmode_delay=seconds
    )

    await ctx.send(
        f"🐌 Slowmode set to **{seconds} seconds**."
    )


# =========================================================
# BOT INFO
# =========================================================

@bot.command(name="botinfo")
async def botinfo(ctx):

    embed = discord.Embed(
        title="🤖 All Rounder",
        description="Your Discord server assistant."
    )

    embed.add_field(
        name="Servers",
        value=str(len(bot.guilds))
    )

    embed.add_field(
        name="Latency",
        value=f"{round(bot.latency * 1000)}ms"
    )

    embed.add_field(
        name="Commands",
        value="Use `!help`"
    )

    await ctx.send(embed=embed)


# =========================================================
# HELP
# =========================================================

@bot.command(name="help")
async def help_command(ctx):

    embed = discord.Embed(
        title="🤖 All Rounder Help",
        description="Available commands"
    )

    embed.add_field(
        name="👋 Basic",
        value=(
            "`!hello`\n"
            "`!hi`\n"
            "`!ping`\n"
            "`!serverinfo`\n"
            "`!userinfo`"
        ),
        inline=False
    )

    embed.add_field(
        name="🛡️ Moderation",
        value=(
            "`!clear`\n"
            "`!timeout`\n"
            "`!kick`\n"
            "`!ban`\n"
            "`!warn`\n"
            "`!warnings`\n"
            "`!lock`\n"
            "`!unlock`\n"
            "`!slowmode`"
        ),
        inline=False
    )

    embed.add_field(
        name="🎮 Fun",
        value=(
            "`!coin`\n"
            "`!dice`\n"
            "`!choose`\n"
            "`!eightball`\n"
            "`!poll`"
        ),
        inline=False
    )

    embed.add_field(
        name="⭐ Level",
        value="`!level`",
        inline=False
    )

    embed.add_field(
        name="⚙️ Setup",
        value=(
            "`!setlog`\n"
            "`!setwelcome`"
        ),
        inline=False
    )

    await ctx.send(embed=embed)


# =========================================================
# ERROR HANDLER
# =========================================================

@bot.event
async def on_command_error(ctx, error):

    if isinstance(error, commands.CommandNotFound):
        return

    if isinstance(error, commands.MissingPermissions):
        await ctx.send(
            "❌ You don't have permission to use this command."
        )
        return

    if isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(
            "❌ Missin
