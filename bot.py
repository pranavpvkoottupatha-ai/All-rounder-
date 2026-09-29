import os
import discord
from discord.ext import commands

TOKEN = os.getenv("DISCORD_TOKEN")

if not TOKEN:
    raise RuntimeError("DISCORD_TOKEN is missing!")

# -----------------------------
# INTENTS
# -----------------------------

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

# -----------------------------
# PREFIX
# -----------------------------

def get_prefix(bot, message):
    return ["!", ""]

# -----------------------------
# BOT
# -----------------------------

bot = commands.Bot(
    command_prefix=get_prefix,
    intents=intents,
    help_command=None
)

# -----------------------------
# READY
# -----------------------------

@bot.event
async def on_ready():
    print(f"Logged in as: {bot.user}")
    print(f"Bot ID: {bot.user.id}")
    print(f"Servers: {len(bot.guilds)}")
    print("All Rounder is ONLINE!")

# -----------------------------
# MESSAGE PROCESSING
# -----------------------------

@bot.event
async def on_message(message):

    if message.author.bot:
        return

    await bot.process_commands(message)

# -----------------------------
# BASIC COMMANDS
# -----------------------------

@bot.command()
async def hi(ctx):
    await ctx.send(f"👋 Hi {ctx.author.mention}!")

@bot.command()
async def hello(ctx):
    await ctx.send(f"👋 Hello {ctx.author.mention}!")

@bot.command()
async def ping(ctx):
    await ctx.send(
        f"🏓 Pong! `{round(bot.latency * 1000)}ms`"
    )

# ============================================================
# TICKET SYSTEM
# ============================================================

TICKET_CATEGORY = "Tickets"


def get_ticket_category(guild):

    for category in guild.categories:
        if category.name == TICKET_CATEGORY:
            return category

    return None


async def create_ticket(ctx):

    guild = ctx.guild
    member = ctx.author

    # Find existing Tickets category
    category = get_ticket_category(guild)

    # Create category if needed
    if category is None:

        try:
            category = await guild.create_category(
                TICKET_CATEGORY,
                reason="All Rounder ticket system"
            )

        except discord.Forbidden:
            await ctx.send(
                "❌ I need **Manage Channels** permission "
                "to create tickets."
            )
            return

        except Exception as e:
            print(f"Category error: {e}")
            await ctx.send(
                "❌ Could not create the Tickets category."
            )
            return

    # Check existing ticket
    for channel in category.text_channels:

        if channel.topic == f"ticket_owner:{member.id}":

            await ctx.send(
                f"⚠️ You already have a ticket: "
                f"{channel.mention}"
            )
            return

    # Safe channel name
    username = "".join(
        c for c in member.name.lower()
        if c.isalnum() or c == "-"
    )

    channel_name = f"ticket-{username}"

    # Permissions
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
            reason="All Rounder ticket"
        )

        await channel.send(
            f"🎫 Welcome {member.mention}!\n\n"
            "Please describe your problem here.\n\n"
            "When finished, use `!close` to close this ticket."
        )

        await ctx.send(
            f"🎫 Ticket created: {channel.mention}"
        )

    except discord.Forbidden:

        await ctx.send(
            "❌ I don't have enough permissions to "
            "create the ticket channel.\n\n"
            "Give me **Manage Channels** permission."
        )

    except Exception as e:

        print(f"Ticket error: {e}")

        await ctx.send(
            "❌ Ticket creation failed."
        )


# -----------------------------
# TICKET COMMAND
# -----------------------------

@bot.command()
@commands.guild_only()
async def ticket(ctx):

    await create_ticket(ctx)


# ============================================================
# CLOSE TICKET
# ============================================================

@bot.command()
@commands.guild_only()
async def close(ctx):

    if ctx.channel.category is None:
        await ctx.send(
            "❌ This is not a ticket channel."
        )
        return

    if ctx.channel.category.name != TICKET_CATEGORY:
        await ctx.send(
            "❌ This is not a ticket channel."
        )
        return

    await ctx.send(
        "🔒 Closing this ticket in 5 seconds..."
    )

    await discord.utils.sleep_until(
        discord.utils.utcnow() +
        __import__("datetime").timedelta(seconds=5)
    )

    try:
        await ctx.channel.delete(
            reason="Ticket closed"
        )

    except discord.Forbidden:
        await ctx.send(
            "❌ I cannot delete this channel."
        )


# ============================================================
# TICKET BUTTON
# ============================================================

class TicketView(discord.ui.View):

    def __init__(self):

        super().__init__(
            timeout=None
        )

    @discord.ui.button(
        label="Create Ticket",
        emoji="🎫",
        style=discord.ButtonStyle.green,
        custom_id="all_rounder_ticket_button"
    )
    async def ticket_button(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        guild = interaction.guild
        member = interaction.user

        if guild is None:
            await interaction.response.send_message(
                "❌ Tickets only work inside a server.",
                ephemeral=True
            )
            return

        # Find category
        category = get_ticket_category(guild)

        if category is None:

            try:

                category = await guild.create_category(
                    TICKET_CATEGORY,
                    reason="All Rounder ticket system"
                )

            except discord.Forbidden:

                await interaction.response.send_message(
                    "❌ I need **Manage Channels** permission.",
                    ephemeral=True
                )
                return

        # Existing ticket
        for channel in category.text_channels:

            if channel.topic == f"ticket_owner:{member.id}":

                await interaction.response.send_message(
                    f"⚠️ You already have a ticket: "
                    f"{channel.mention}",
                    ephemeral=True
                )
                return

        username = "".join(
            c for c in member.name.lower()
            if c.isalnum() or c == "-"
        )

        channel_name = f"ticket-{username}"

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
                reason="All Rounder ticket"
            )

            await channel.send(
                f"🎫 Welcome {member.mention}!\n\n"
                "Please describe your problem here.\n\n"
                "Use `!close` when finished."
            )

            await interaction.response.send_message(
                f"🎫 Your ticket was created: "
                f"{channel.mention}",
                ephemeral=True
            )

        except discord.Forbidden:

            await interaction.response.send_message(
                "❌ I need **Manage Channels** permission.",
                ephemeral=True
            )


# ============================================================
# TICKET PANEL
# ============================================================

@bot.command()
@commands.guild_only()
@commands.has_permissions(manage_channels=True)
async def ticketpanel(ctx):

    embed = discord.Embed(
        title="🎫 All Rounder Support",
        description=(
            "Need help?\n\n"
            "Click the button below to create "
            "a private support ticket."
        ),
        color=discord.Color.blue()
    )

    await ctx.send(
        embed=embed,
        view=TicketView()
    )


# ============================================================
# HELP
# ============================================================

@bot.command()
async def help(ctx):

    await ctx.send(
        "**🤖 All Rounder Commands**\n\n"
        "👋 `hi`\n"
        "👋 `hello`\n"
        "🏓 `ping`\n\n"
        "🎫 `ticket` — Create a ticket\n"
        "🔒 `close` — Close ticket\n"
        "🎫 `ticketpanel` — Create ticket button\n\n"
        "Commands also work with `!`."
    )


# ============================================================
# ERROR HANDLER
# ============================================================

@bot.event
async def on_command_error(ctx, error):

    if isinstance(error, commands.CommandNotFound):
        return

    if isinstance(error, commands.MissingPermissions):
        await ctx.send(
            "❌ You don't have permission "
            "to use this command."
        )
        return

    if isinstance(error, commands.NoPrivateMessage):
        await ctx.send(
            "❌ This command only works inside a server."
        )
        return

    print(f"Command error: {error}")


# ============================================================
# START
# ============================================================

print("Starting All Rounder...")

bot.run(TOKEN)
