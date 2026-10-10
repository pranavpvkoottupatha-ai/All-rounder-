
import os
import re
import random
import json
import discord
from datetime import timedelta
from discord.ext import commands

TOKEN = os.getenv("DISCORD_TOKEN")
if not TOKEN:
    raise RuntimeError("DISCORD_TOKEN secret is missing!")

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

TICKET_CATEGORY = "Tickets"
WARNINGS_FILE = "warnings.json"


def get_prefix(bot, message):
    return ["!", ""]


bot = commands.Bot(
    command_prefix=get_prefix,
    intents=intents,
    help_command=None
)

warnings = {}
if os.path.exists(WARNINGS_FILE):
    try:
        with open(WARNINGS_FILE, "r", encoding="utf-8") as f:
            warnings = json.load(f)
    except (json.JSONDecodeError, OSError):
        warnings = {}


def save_warnings():
    try:
        with open(WARNINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(warnings, f, indent=2)
    except OSError as e:
        print(f"Warning save error: {e}")


# ---------------- BASIC ----------------

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")
    print(f"Servers: {len(bot.guilds)}")
    print("All Rounder is ONLINE!")
    await bot.change_presence(
        activity=discord.Game(name="!help | All Rounder")
    )


@bot.command()
async def hi(ctx):
    await ctx.send(f"👋 Hi {ctx.author.mention}!")


@bot.command()
async def hello(ctx):
    await ctx.send(f"Hello, {ctx.author.mention}!")


@bot.command()
async def ping(ctx):
    await ctx.send(f"🏓 Pong! {round(bot.latency * 1000)} ms")


@bot.command()
async def botinfo(ctx):
    await ctx.send(
        f"🤖 **All Rounder**\n"
        f"Servers: {len(bot.guilds)}\n"
        f"Latency: {round(bot.latency * 1000)} ms"
    )


@bot.command()
@commands.guild_only()
async def serverinfo(ctx):
    g = ctx.guild
    embed = discord.Embed(
        title=f"🌐 {g.name}",
        color=discord.Color.blue()
    )
    embed.add_field(name="Members", value=g.member_count or "Unknown")
    embed.add_field(name="Channels", value=len(g.channels))
    embed.add_field(name="Roles", value=len(g.roles))
    await ctx.send(embed=embed)


@bot.command()
@commands.guild_only()
async def userinfo(ctx, member: discord.Member = None):
    member = member or ctx.author
    await ctx.send(
        f"👤 **{member}**\n"
        f"ID: `{member.id}`\n"
        f"Account created: <t:{int(member.created_at.timestamp())}:D>"
    )


# ---------------- FUN ----------------

@bot.command()
async def coin(ctx):
    await ctx.send(f"🪙 {random.choice(['Heads', 'Tails'])}!")


@bot.command()
async def dice(ctx):
    await ctx.send(f"🎲 You rolled **{random.randint(1, 6)}**!")


@bot.command()
async def choose(ctx, *, options: str):
    choices = [x.strip() for x in options.split(",") if x.strip()]
    if len(choices) < 2:
        await ctx.send("Usage: `!choose pizza, burger, dosa`")
        return
    await ctx.send(f"🤔 I choose **{random.choice(choices)}**!")


@bot.command()
async def poll(ctx, *, question: str):
    msg = await ctx.send(f"📊 **Poll**\n{question}\n\n👍 Yes\n👎 No")
    await msg.add_reaction("👍")
    await msg.add_reaction("👎")


# ---------------- MODERATION ----------------

@bot.command()
@commands.guild_only()
@commands.has_permissions(manage_messages=True)
@commands.bot_has_permissions(manage_messages=True)
async def clear(ctx, amount: int = 10):
    amount = max(1, min(amount, 100))
    deleted = await ctx.channel.purge(limit=amount + 1)
    await ctx.send(f"🧹 Deleted {max(0, len(deleted) - 1)} messages.",
                   delete_after=5)


@bot.command()
@commands.guild_only()
@commands.has_permissions(moderate_members=True)
@commands.bot_has_permissions(moderate_members=True)
async def timeout(ctx, member: discord.Member, minutes: int = 5, *, reason="No reason provided"):
    if member == ctx.author or member == ctx.guild.me:
        await ctx.send("❌ You can't timeout yourself or the bot.")
        return
    minutes = max(1, min(minutes, 40320))
    await member.timeout(timedelta(minutes=minutes), reason=reason)
    await ctx.send(f"🔇 {member.mention} timed out for {minutes} minute(s). Reason: {reason}")


@bot.command()
@commands.guild_only()
@commands.has_permissions(kick_members=True)
@commands.bot_has_permissions(kick_members=True)
async def kick(ctx, member: discord.Member, *, reason="No reason provided"):
    await member.kick(reason=reason)
    await ctx.send(f"👢 {member} was kicked. Reason: {reason}")


@bot.command()
@commands.guild_only()
@commands.has_permissions(ban_members=True)
@commands.bot_has_permissions(ban_members=True)
async def ban(ctx, member: discord.Member, *, reason="No reason provided"):
    await member.ban(reason=reason)
    await ctx.send(f"🔨 {member} was banned. Reason: {reason}")


@bot.command()
@commands.guild_only()
@commands.has_permissions(moderate_members=True)
async def warn(ctx, member: discord.Member, *, reason="No reason provided"):
    gid, uid = str(ctx.guild.id), str(member.id)
    warnings.setdefault(gid, {}).setdefault(uid, []).append(reason)
    save_warnings()
    count = len(warnings[gid][uid])
    await ctx.send(f"⚠️ {member.mention} warned. Total warnings: {count}")


@bot.command(name="warnings")
@commands.guild_only()
async def warnings_command(ctx, member: discord.Member = None):
    member = member or ctx.author
    items = warnings.get(str(ctx.guild.id), {}).get(str(member.id), [])
    if not items:
        await ctx.send(f"✅ {member.mention} has no saved warnings.")
        return
    await ctx.send(
        f"⚠️ Warnings for **{member}**:\n" +
        "\n".join(f"{i}. {reason}" for i, reason in enumerate(items, 1))
    )


@bot.command()
@commands.guild_only()
@commands.has_permissions(manage_channels=True)
@commands.bot_has_permissions(manage_channels=True)
async def lock(ctx):
    await ctx.channel.set_permissions(
        ctx.guild.default_role, send_messages=False
    )
    await ctx.send("🔒 Channel locked.")


@bot.command()
@commands.guild_only()
@commands.has_permissions(manage_channels=True)
@commands.bot_has_permissions(manage_channels=True)
async def unlock(ctx):
    await ctx.channel.set_permissions(
        ctx.guild.default_role, send_messages=None
    )
    await ctx.send("🔓 Channel unlocked.")


@bot.command()
@commands.guild_only()
@commands.has_permissions(manage_channels=True)
async def slowmode(ctx, seconds: int = 5):
    seconds = max(0, min(seconds, 21600))
    await ctx.channel.edit(slowmode_delay=seconds)
    await ctx.send(f"🐢 Slowmode: {seconds} seconds.")


# ---------------- TICKET HELPERS ----------------

def ticket_category(guild):
    return discord.utils.get(guild.categories, name=TICKET_CATEGORY)


def ticket_owner(channel):
    topic = channel.topic or ""
    match = re.fullmatch(r"ticket_owner:(\d+)", topic)
    return int(match.group(1)) if match else None


def is_staff(member):
    return (
        member.guild_permissions.administrator
        or member.guild_permissions.manage_channels
        or any(role.name.lower() == "staff" for role in member.roles)
    )


async def make_ticket(guild, member):
    me = guild.me
    if me is None:
        return None, "I couldn't identify my bot member in this server."

    perms = guild.me.guild_permissions
    needed = {
        "Manage Channels": perms.manage_channels,
        "View Channels": perms.view_channel,
        "Send Messages": perms.send_messages,
        "Read Message History": perms.read_message_history,
    }
    missing = [name for name, allowed in needed.items() if not allowed]
    if missing:
        return None, "Missing bot server permissions:\n" + "\n".join(
            f"❌ {name}" for name in missing
        )

    category = ticket_category(guild)
    try:
        if category is None:
            category = await guild.create_category(
                TICKET_CATEGORY, reason="All Rounder tickets"
            )

        for channel in category.text_channels:
            if ticket_owner(channel) == member.id:
                return channel, "You already have an open ticket."

        username = re.sub(r"[^a-z0-9-]", "-", member.name.lower())[:80]
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            member: discord.PermissionOverwrite(
                view_channel=True, send_messages=True,
                read_message_history=True, attach_files=True
            ),
            me: discord.PermissionOverwrite(
                view_channel=True, send_messages=True,
                read_message_history=True, manage_channels=True
            ),
        }

        staff = discord.utils.get(guild.roles, name="Staff")
        if staff:
            overwrites[staff] = discord.PermissionOverwrite(
                view_channel=True, send_messages=True,
                read_message_history=True
            )

        channel = await guild.create_text_channel(
            f"ticket-{username}",
            category=category,
            topic=f"ticket_owner:{member.id}",
            overwrites=overwrites,
            reason=f"Ticket requested by {member}"
        )
        await channel.send(
            f"🎫 Welcome {member.mention}!\n"
            "Describe your issue here. Use `!close` when finished."
        )
        return channel, None

    except discord.Forbidden:
        return None, (
            "Discord denied ticket creation. Check the bot's **Manage Channels** "
            "permission and any explicit Deny rules in server/category permissions."
        )
    except discord.HTTPException as e:
        print(f"Ticket HTTP error: {e}")
        return None, f"Discord API error: `{e.code}` — {e.text[:250]}"


# ---------------- TICKET COMMANDS ----------------

@bot.command()
@commands.guild_only()
async def ticket(ctx):
    channel, error = await make_ticket(ctx.guild, ctx.author)
    if error:
        await ctx.send(f"❌ {error}" + (f"\nExisting ticket: {channel.mention}" if channel else ""))
    else:
        await ctx.send(f"🎫 Ticket created: {channel.mention}")


@bot.command()
@commands.guild_only()
async def close(ctx):
    owner = ticket_owner(ctx.channel)
    if owner is None:
        await ctx.send("❌ This isn't an All Rounder ticket channel.")
        return
    if ctx.author.id != owner and not is_staff(ctx.author):
        await ctx.send("❌ Only the ticket owner or staff can close this ticket.")
        return
    await ctx.send("🔒 Closing ticket in 5 seconds...")
    import asyncio
    await asyncio.sleep(5)
    try:
        await ctx.channel.delete(reason=f"Ticket closed by {ctx.author}")
    except discord.Forbidden:
        print("Ticket close failed: bot needs Manage Channels.")


@bot.command()
@commands.guild_only()
async def add(ctx, member: discord.Member):
    if ticket_owner(ctx.channel) is None:
        await ctx.send("❌ Use this inside a ticket.")
        return
    if ctx.author.id != ticket_owner(ctx.channel) and not is_staff(ctx.author):
        await ctx.send("❌ Only the owner or staff can add members.")
        return
    try:
        await ctx.channel.set_permissions(
            member, view_channel=True, send_messages=True,
            read_message_history=True, attach_files=True
        )
        await ctx.send(f"✅ Added {member.mention} to this ticket.")
    except discord.Forbidden:
        await ctx.send("❌ The bot needs Manage Channels permission.")


@bot.command()
@commands.guild_only()
async def remove(ctx, member: discord.Member):
    owner = ticket_owner(ctx.channel)
    if owner is None:
        await ctx.send("❌ Use this inside a ticket.")
        return
    if ctx.author.id != owner and not is_staff(ctx.author):
        await ctx.send("❌ Only the owner or staff can remove members.")
        return
    if member.id == owner:
        await ctx.send("❌ You can't remove the ticket owner.")
        return
    try:
        await ctx.channel.set_permissions(member, overwrite=None)
        await ctx.send(f"✅ Removed {member.mention} from this ticket.")
    except discord.Forbidden:
        await ctx.send("❌ The bot needs Manage Channels permission.")


class TicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Create Ticket", emoji="🎫",
        style=discord.ButtonStyle.green,
        custom_id="all_rounder_ticket_create"
    )
    async def create_button(self, interaction, button):
        if interaction.guild is None:
            await interaction.response.send_message(
                "Tickets only work in a server.", ephemeral=True
            )
            return

        await interaction.response.defer(ephemeral=True)
        channel, error = await make_ticket(
            interaction.guild, interaction.user
        )
        if error:
            await interaction.followup.send(
                f"❌ {error}" + (f"\nExisting ticket: {channel.mention}" if channel else ""),
                ephemeral=True
            )
        else:
            await interaction.followup.send(
                f"🎫 Ticket created: {channel.mention}", ephemeral=True
            )


@bot.command()
@commands.guild_only()
@commands.has_permissions(manage_channels=True)
async def ticketpanel(ctx):
    embed = discord.Embed(
        title="🎫 All Rounder Support",
        description="Click **Create Ticket** to open a private support channel.",
        color=discord.Color.blue()
    )
    await ctx.send(embed=embed, view=TicketView())


# ---------------- PERMISSION DIAGNOSTICS ----------------

@bot.command()
@commands.guild_only()
async def botperms(ctx):
    me = ctx.guild.me
    guild_perms = me.guild_permissions
    channel_perms = ctx.channel.permissions_for(me)

    checks = {
        "Manage Channels (server)": guild_perms.manage_channels,
        "View Channel (current channel)": channel_perms.view_channel,
        "Send Messages (current channel)": channel_perms.send_messages,
        "Read Message History (current channel)": channel_perms.read_message_history,
    }
    report = "\n".join(
        f"{'✅' if allowed else '❌'} {name}"
        for name, allowed in checks.items()
    )
    await ctx.send(f"**🔎 All Rounder Permission Report**\n{report}")


# ---------------- HELP ----------------

@bot.command()
async def help(ctx):
    embed = discord.Embed(
        title="🤖 All Rounder Commands",
        color=discord.Color.gold()
    )
    embed.add_field(
        name="Basic",
        value="`!hi` `!hello` `!ping` `!botinfo` `!serverinfo` `!userinfo`",
        inline=False
    )
    embed.add_field(
        name="Fun",
        value="`!coin` `!dice` `!choose red, blue` `!poll question`",
        inline=False
    )
    embed.add_field(
        name="Moderation",
        value="`!clear 10` `!timeout @user 5 reason` `!kick @user` "
              "`!ban @user` `!warn @user reason` `!warnings` "
              "`!lock` `!unlock` `!slowmode 5`",
        inline=False
    )
    embed.add_field(
        name="Tickets",
        value="`!ticket` `!ticketpanel` `!close` `!add @user` `!remove @user`",
        inline=False
    )
    embed.add_field(name="Diagnostics", value="`!botperms`", inline=False)
    await ctx.send(embed=embed)


# ---------------- ERRORS ----------------

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        return
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("❌ You don't have permission to run that command.")
        return
    if isinstance(error, commands.BotMissingPermissions):
        await ctx.send("❌ Bot is missing: " + ", ".join(error.missing_permissions))
        return
    if isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(f"❌ Missing argument: `{error.param.name}`")
        return
    if isinstance(error, commands.MemberNotFound):
        await ctx.send("❌ Member not found. Try mentioning them.")
        return
    if isinstance(error, commands.NoPrivateMessage):
        await ctx.send("❌ Use this command inside a server.")
        return
    print(f"Command error: {type(error).__name__}: {error}")
    await ctx.send(f"❌ Command failed: `{type(error).__name__}`")


# ---------------- START ----------------

print("Starting All Rounder...")
bot.run(TOKEN)
    
