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
    raise RuntimeError("DISCORD_TOKEN secret was not found.")


# ============================================================
# INTENTS
# ============================================================

intents = discord.Intents.default()
intents.message_content = True
intents.members = True


# ============================================================
# COMMAND PREFIX
# ============================================================

def get_prefix(bot, message):

    content = message.content.strip()

    if not content:
        return ["!"]

    first_word = content.split()[0].lower()
    command_name = first_word.lstrip("!")

    if bot.get_command(command_name):
        return ["", "!"]

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

        if member.guild_permissions.administrator:
            return

        await member.timeout(
            timedelta(minutes=1),
            reason=reason
        )

        await message.channel.send(
            f"⚠️ {member.mention} was timed out "
            f"for 1 minute.\n"
            f"**Reason:** {reason}"
        )

    except discord.Forbidden:

        print("❌ Missing permission to timeout member.")

    except Exception as error:

        print(f"❌ Anti-spam error: {error}")


# ============================================================
# READY
# ============================================================

@bot.event
async def on_ready():

    print(f"Logged in as: {bot.user}")
    print(f"Bot ID: {bot.user.id}")
    print(f"Servers: {len(bot.guilds)}")
    print("All Rounder is ONLINE!")

    try:

        await bot.change_presence(
            activity=discord.Game(
                name="Type help or !help"
            )
        )

    except Exception as error:

        print(f"Presence error: {error}")


# ============================================================
# MEMBER JOIN
# ============================================================

@bot.event
async def on_member_join(member):

    channel = discord.utils.find(
        lambda c: c.name.lower() in [
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
        lambda c: c.name.lower() in [
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
# MESSAGE / ANTI-SPAM
# ============================================================

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

    while (
        history
        and now - history[0]["time"] > SPAM_TIME
    ):
        history.popleft()


    # --------------------------------------------------------
    # 5 MESSAGES / 5 SECONDS
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
    # REPEATED MESSAGE
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
    # DISCORD INVITE
    # --------------------------------------------------------

    if INVITE_PATTERN.search(message.content):

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
    # MASS MENTION
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

    await ctx.send(embed=embed)


# ============================================================
# USER INFO
# ============================================================

@bot.command()
async def userinfo(
    ctx,
    member: discord.Member = None
):

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
            member.joined_at.strftime("%d %B %Y")
            if member.joined_at
            else "Unknown"
        ),
        inline=False
    )

    await ctx.send(embed=embed)


# ============================================================
# CLEAR
# ============================================================

@bot.command()
@commands.has_permissions(manage_messages=True)
async def clear(
    ctx,
    amount: int = 10
):

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

    await msg.delete(delay=5)


# ============================================================
# TIMEOUT
# ============================================================

@bot.command()
@commands.has_permissions(moderate_members=True)
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

    await member.kick(reason=reason)

    await ctx.send(
        f"👢 {member.mention} was kicked.\n"
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

    await member.ban(reason=reason)

    await ctx.send(
        f"🔨 {member.mention} was banned.\n"
        f"**Reason:** {reason}"
    )


# ============================================================
# WARN
# ============================================================

warnings = defaultdict(list)


@bot.command()
@commands.has_permissions(moderate_members=True)
async def warn(
    ctx,
    member: discord.Member,
    *,
    reason="No reason provided"
):

    warnings[member.id].append(reason)

    await ctx.send(
        f"⚠️ {member.mention} has been warned.\n"
        f"**Reason:** {reason}"
    )


# ============================================================
# WARNINGS
# ============================================================

@bot.command(name="warnings")
async def warnings_command(
    ctx,
    member: discord.Member = None
):

    member = member or ctx.author

    user_warnings = warnings.get(
        member.id,
        []
    )

    if not user_warnings:

        await ctx.send(
            f"✅ {member.mention} has no warnings."
        )

        return

    text = "\n".join(
        f"{i + 1}. {reason}"
        for i, reason in enumerate(user_warnings)
    )

    await ctx.send(
        f"⚠️ Warnings for {member.mention}:\n"
        f"{text}"
    )


# ============================================================
# COIN
# ============================================================

@bot.command()
async def coin(ctx):

    result = random.choice(
        ["Heads", "Tails"]
    )

    await ctx.send(
        f"🪙 **{result}!**"
    )


# ============================================================
# DICE
# ============================================================

@bot.command()
async def dice(ctx):

    result = random.randint(1, 6)

    await ctx.send(
        f"🎲 You rolled **{result}**!"
    )


# ============================================================
# CHOOSE
# ============================================================

@bot.command()
async def choose(
    ctx,
    *choices
):

    if len(choices) < 2:

        await ctx.send(
            "❌ Give me at least two choices."
        )

        return

    result = random.choice(choices)

    await ctx.send(
        f"🤔 I choose **{result}**!"
    )


# ============================================================
# EIGHT BALL
# ============================================================

@bot.command(name="eightball")
async def eightball(
    ctx,
    *,
    question=None
):

    if not question:

        await ctx.send(
            "🎱 Ask me a question!"
        )

        return

    answers = [
        "Yes! ✅",
        "No. ❌",
        "Maybe. 🤔",
        "Definitely! 🔥",
        "Not sure. 😅",
        "Ask again later. 🔮"
    ]

    await ctx.send(
        f"🎱 **{random.choice(answers)}**"
    )


# ============================================================
# POLL
# ============================================================

@bot.command()
async def poll(
    ctx,
    *,
    question
):

    message = await ctx.send(
        f"📊 **Poll**\n\n"
        f"{question}\n\n"
        f"👍 = Yes\n"
        f"👎 = No"
    )

    await message.add_reaction("👍")
    await message.add_reaction("👎")


# ============================================================
# LOCK
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

    await ctx.send(
        "🔒 Channel locked."
    )


# ============================================================
# UNLOCK
# ============================================================

@bot.command()
@commands.has_permissions(manage_channels=True)
async def unlock(ctx):

    overwrite = ctx.channel.overwrites_for(
        ctx.guild.default_role
    )

    overwrite.send_messages = None

    await ctx.channel.set_permissions(
        ctx.guild.default_role,
        overwrite=overwrite
    )

    await ctx.send(
        "🔓 Channel unlocked."
    )


# ============================================================
# SLOWMODE
# ============================================================

@bot.command()
@commands.has_permissions(manage_channels=True)
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
        f"🐢 Slowmode set to **{seconds} seconds**."
    )


# ============================================================
# BOT INFO
# ============================================================

@bot.command()
async def botinfo(ctx):

    latency = round(bot.latency * 1000)

    embed = discord.Embed(
        title="🤖 All Rounder",
        description="Your Discord server assistant.",
        color=discord.Color.gold()
    )

    embed.add_field(
        name="Servers",
        value=len(bot.guilds),
        inline=True
    )

    embed.add_field(
        name="Latency",
        value=f"{latency}ms",
        inline=True
    )

    embed.add_field(
        name="Prefix",
        value="`!` or no prefix",
        inline=False
    )

    embed.add_field(
        name="Anti-Spam",
        value="5 messages / 5 seconds",
        inline=False
    )

    await ctx.send(embed=embed)


# ============================================================
# TICKET SYSTEM
# ============================================================

TICKET_CATEGORY_NAME = "Tickets"


def get_ticket_category(guild):

    return discord.utils.get(
        guild.categories,
        name=TICKET_CATEGORY_NAME
    )


async def create_ticket_category(guild):

    category = get_ticket_category(guild)

    if category:
        return category

    try:

        category = await guild.create_category(
            TICKET_CATEGORY_NAME,
            reason="All Rounder ticket system"
        )

        return category

    except discord.Forbidden:

        return None


def is_ticket_channel(channel):

    return (
        isinstance(channel, discord.TextChannel)
        and channel.category is not None
        and channel.category.name == TICKET_CATEGORY_NAME
    )


# ============================================================
# CREATE TICKET
# ============================================================

async def create_ticket(
    guild,
    member
):

    category = await create_ticket_category(guild)

    if category is None:
        return None, "❌ I don't have permission to create a ticket category."

    # Check if user already has a ticket
    for channel in category.text_channels:

        if channel.topic == f"ticket_owner:{member.id}":

            return channel, "⚠️ You already have an open ticket."


    channel_name = (
        f"ticket-{member.name.lower()}"
    )

    # Discord channel names can only contain
    # lowercase letters, numbers, and hyphens.
    channel_name = re.sub(
        r"[^a-z0-9-]",
        "-",
        channel_name
    )

    channel_name = channel_name[:90]

    overwrites = {

        guild.default_role:
            discord.PermissionOverwrite(
                view_channel=False
            ),

        member:
            discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                read_message_history=True,
                attach_files=True
            ),

        guild.me:
            discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                read_message_history=True,
                manage_channels=True,
                manage_messages=True
            )
    }

    try:

        channel = await guild.create_text_channel(
            channel_name,
            category=category,
            topic=f"ticket_owner:{member.id}",
            overwrites=overwrites,
            reason="All Rounder ticket creation"
        )

        await channel.send(
            f"🎫 Welcome {member.mention}!\n\n"
            f"Please describe your issue and our staff "
            f"can help you.\n\n"
            f"Use `close` or `!close` when you are finished."
        )

        return channel, None

    except discord.Forbidden:

        return None, (
            "❌ I don't have permission to create "
            "ticket channels."
        )

    except Exception as error:

        print(f"Ticket creation error: {error}")

        return None, (
            "❌ Something went wrong while creating "
            "the ticket."
        )


# ============================================================
# TICKET COMMAND
# ============================================================

@bot.command()
@commands.guild_only()
async def ticket(ctx):

    channel, error = await create_ticket(
        ctx.guild,
        ctx.author
    )

    if error:

        await ctx.send(error)

        if channel:
            await ctx.send(
                f"🎫 Your existing ticket is: "
                f"{channel.mention}"
            )

        return

    await ctx.send(
        f"🎫 Your ticket has been created: "
        f"{channel.mention}"
    )


# =======================

   
