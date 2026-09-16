import os
import random
import re
import time
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
# ANTI-SPAM
# =========================================================

message_history = defaultdict(
    lambda: deque(maxlen=10)
)

SPAM_LIMIT = 6
SPAM_TIME = 7

INVITE_PATTERN = re.compile(
    r"(discord\.gg/|discord\.com/invite/)",
    re.IGNORECASE
)


async def punish_spammer(message, reason):
    member = message.author

    try:
        if isinstance(member, discord.Member):

            if member.guild_permissions.administrator:
                return

            await member.timeout(
                timedelta(minutes=1),
                reason=reason
            )

            await message.channel.send(
                f"⚠️ {member.mention} was timed out for 1 minute.\n"
                f"Reason: {reason}"
            )

    except discord.Forbidden:
        print("Missing permission to timeout member.")

    except Exception as e:
        print(f"Anti-spam error: {e}")


# =========================================================
# BOT READY
# =========================================================

@bot.event
async def on_ready():

    print("-----------------------------------")
    print(f"Logged in as: {bot.user}")
    print(f"Bot ID: {bot.user.id}")
    print(f"Servers: {len(bot.guilds)}")
    print("All Rounder is ONLINE!")
    print("-----------------------------------")

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

    print(
        f"{member} joined {member.guild.name}"
    )


# =========================================================
# MEMBER LEAVE
# =========================================================

@bot.event
async def on_member_remove(member):

    print(
        f"{member} left {member.guild.name}"
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

    history.append(
        {
            "time": now,
            "content": message.content
        }
    )

    # Remove old messages
    while history and now - history[0]["time"] > SPAM_TIME:
        history.popleft()

    # Rapid-message spam
    if len(history) >= SPAM_LIMIT:

        await punish_spammer(
            message,
            "Too many messages in a short time."
        )

        history.clear()
        return

    # Repeated messages
    recent = [
        item["content"]
        for item in list(history)[-3:]
    ]

    if len(recent) == 3 and len(set(recent)) == 1:

        await punish_spammer(
            message,
            "Repeated messages detected."
        )

        history.clear()
        return

    # Discord invite detection
    if INVITE_PATTERN.search(message.content):

        await punish_spammer(
            message,
            "Discord invite detected."
        )

        return

    # Mass mention detection
    if len(message.mentions) >= 5:

        await punish_spammer(
            message,
            "Mass mentions detected."
        )

        return

    await bot.process_commands(message)


# =========================================================
# !HELLO
# =========================================================

@bot.command(name="hello")
async def hello(ctx):

    await ctx.send(
        f"👋 Hello {ctx.author.mention}! "
        f"I'm **All Rounder**."
    )


# =========================================================
# !HI
# =========================================================

@bot.command(name="hi")
async def hi(ctx):

    await ctx.send(
        f"👋 Hi {ctx.author.mention}!"
    )


# =========================================================
# !PING
# =========================================================

@bot.command(name="ping")
async def ping(ctx):

    latency = round(
        bot.latency * 1000
    )

    await ctx.send(
        f"🏓 Pong! **{latency}ms**"
    )


# =========================================================
# !SERVERINFO
# =========================================================

@bot.command(name="serverinfo")
async def serverinfo(ctx):

    guild = ctx.guild

    embed = discord.Embed(
        title="📊 Server Information"
    )

    embed.add_field(
        name="Server",
        value=guild.name,
        inline=False
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
        name="Server ID",
        value=str(guild.id)
    )

    await ctx.send(
        embed=embed
    )


# =========================================================
# !USERINFO
# =========================================================

@bot.command(name="userinfo")
async def userinfo(
    ctx,
    member: discord.Member = None
):

    member = member or ctx.author

    embed = discord.Embed(
        title="👤 User Information"
    )

    embed.add_field(
        name="User",
        value=str(member),
        inline=False
    )

    embed.add_field(
        name="ID",
        value=str(member.id)
    )

    embed.add_field(
        name="Bot",
        value="Yes" if member.bot else "No"
    )

    await ctx.send(
        embed=embed
    )


# =========================================================
# !CLEAR
# =========================================================

@bot.command(name="clear")
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
        f"🧹 Deleted **{len(deleted) - 1}** messages."
    )

    await msg.delete(delay=3)


# =========================================================
# !TIMEOUT
# =========================================================

@bot.command(name="timeout")
@commands.has_permissions(
    moderate_members=True
)
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
        f"⏱️ {member.mention} was timed out "
        f"for **{minutes} minutes**.\n"
        f"Reason: {reason}"
    )


# =========================================================
# !KICK
# =========================================================

@bot.command(name="kick")
@commands.has_permissions(
    kick_members=True
)
async def kick(
    ctx,
    member: discord.Member,
    *,
    reason="No reason provided"
):

    await member.kick(
        reason=reason
    )

    await ctx.send(
        f"👢 **{member}** was kicked.\n"
        f"Reason: {reason}"
    )


# =========================================================
# !BAN
# =========================================================

@bot.command(name="ban")
@commands.has_permissions(
    ban_members=True
)
async def ban(
    ctx,
    member: discord.Member,
    *,
    reason="No reason provided"
):

    await member.ban(
        reason=reason
    )

    await ctx.send(
        f"🔨 **{member}** was banned.\n"
        f"Reason: {reason}"
    )


# =========================================================
# !WARN
# =========================================================

warnings = defaultdict(int)


@bot.command(name="warn")
@commands.has_permissions(
    moderate_members=True
)
async def warn(
    ctx,
    member: discord.Member,
    *,
    reason="No reason provided"
):

    warnings[member.id] += 1

    await ctx.send(
        f"⚠️ {member.mention} has been warned.\n"
        f"Warnings: **{warnings[member.id]}**\n"
        f"Reason: {reason}"
    )


# =========================================================
# !WARNINGS
# =========================================================

@bot.command(name="warnings")
async def warning_count(
    ctx,
    member: discord.Member = None
):

    member = member or ctx.author

    count = warnings[member.id]

    await ctx.send(
        f"⚠️ **{member}** has "
        f"**{count}** warning(s)."
    )


# =========================================================
# !COIN
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
# !DICE
# =========================================================

@bot.command(name="dice")
async def dice(ctx):

    number = random.randint(1, 6)

    await ctx.send(
        f"🎲 You rolled **{number}**!"
    )


# =========================================================
# !CHOOSE
# =========================================================

@bot.command(name="choose")
async def choose(ctx, *choices):

    if len(choices) < 2:

        await ctx.send(
            "❌ Give me at least two choices.\n"
            "Example: `!choose pizza burger`"
        )

        return

    result = random.choice(
        choices
    )

    await ctx.send(
        f"🎯 I choose: **{result}**"
    )


# =========================================================
# !EIGHTBALL
# =========================================================

@bot.command(name="eightball")
async def eightball(
    ctx,
    *,
    question=""
):

    if not question:

        await ctx.send(
            "🔮 Ask me a question!"
        )

        return

    answers = [
        "Yes 👍",
        "No 👎",
        "Maybe 🤔",
        "Definitely! ✅",
        "Ask again later 🔮",
        "I don't know 😅"
    ]

    await ctx.send(
        f"🔮 **{random.choice(answers)}**"
    )


# =========================================================
# !POLL
# =========================================================

@bot.command(name="poll")
async def poll(
    ctx,
    *,
    question
):

    embed = discord.Embed(
        title="📊 Poll",
        description=question
    )

    msg = await ctx.send(
        embed=embed
    )

    await msg.add_reaction("👍")
    await msg.add_reaction("👎")


# =========================================================
# !LOCK
# =========================================================

@bot.command(name="lock")
@commands.has_permissions(
    manage_channels=True
)
async def lock(ctx):

    overwrite = ctx.channel.overwrites_for(
        ctx.guild.default_role
    )

    overwrite.send_messages = False

    await ctx.channel.set_permissions(
        ctx.guild.default_role,
        overwrite=overwrite
    )

    await ctx.send(
        "🔒 Channel locked."
    )


# =========================================================
# !UNLOCK
# =========================================================

@bot.command(name="unlock")
@commands.has_permissions(
    manage_channels=True
)
async def unlock(ctx):

    overwrite = ctx.channel.overwrites_for(
        ctx.guild.default_role
    )

    overwrite.send_messages = True

    await ctx.channel.set_permissions(
        ctx.guild.default_role,
        overwrite=overwrite
    )

    await ctx.send(
        "🔓 Channel unlocked."
    )


# =========================================================
# !SLOWMODE
# =========================================================

@bot.command(name="slowmode")
@commands.has_permissions(
    manage_channels=True
)
async def slowmode(
    ctx,
    seconds: int = 0
):

    if seconds < 0:
        seconds = 0

    if seconds > 21600:
        seconds = 21600

    await ctx.channel.edit(
        slowmode_delay=seconds
    )

    await ctx.send(
        f"🐌 Slowmode: **{seconds} seconds**"
    )


# =========================================================
# !BOTINFO
# =========================================================

@bot.command(name="botinfo")
async def botinfo(ctx):

    embed = discord.Embed(
        title="🤖 All Rounder",
        description="Discord server assistant"
    )

    embed.add_field(
        name="Servers",
        value=str(len(bot.guilds))
    )

    embed.add_field(
        name="Latency",
        value=f"{round(bot.latency * 1000)}ms"
    )

    await ctx.send(
        embed=embed
    )


# =========================================================
# !HELP
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
        name="🤖 Bot",
        value=(
            "`!botinfo`\n"
            "`!help`"
        ),
        inline=False
    )

    await ctx.send(
        embed=embed
    )


# =========================================================
# ERROR HANDLER
# =========================================================

@bot.event
async def on_command_error(
    ctx,
    error
):

    if isinstance(
        error,
        commands.CommandNotFound
    ):
        return

    if isinstance(
        error,
        commands.MissingPermissions
    ):
        await ctx.send(
            "❌ You don't have permission "
            "to use this command."
        )
        return

    if isinstance(
        error,
        commands.MissingRequiredArgument
    ):
        await ctx.send(
            "❌ Missing an argument. "
            "Use `!help` for help."
        )
        return

    if isinstance(
        error,
        commands.MemberNotFound
    ):
        await ctx.send(
            "❌ I couldn't find that member."
        )
        return

    if isinstance(
        error,
        commands.BadArgument
    ):
        await ctx.send(
            "❌ Invalid argument."
        )
        return

    print(
        f"Command error: {repr(error)}"
    )

    await ctx.send(
        "❌ Something went wrong."
    )


# =========================================================
# START
# =========================================================

print("Starting All Rounder...")

bot.run(TOKEN)
