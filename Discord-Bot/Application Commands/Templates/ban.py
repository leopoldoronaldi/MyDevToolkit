import asyncio
import datetime
from typing import Optional

import discord
from discord import app_commands
from discord.ext import commands

UNIT_CHOICES = [
    app_commands.Choice(name="Minutes", value="minutes"),
    app_commands.Choice(name="Hours",   value="hours"),
    app_commands.Choice(name="Days",    value="days"),
    app_commands.Choice(name="Weeks",   value="weeks"),
    app_commands.Choice(name="Months",  value="months"),
    app_commands.Choice(name="Years",   value="years"),
]


def resolve_duration(amount: int, unit: str) -> datetime.timedelta:
    """Convert amount + unit into a timedelta."""
    match unit.lower():
        case "minutes": return datetime.timedelta(minutes=amount)
        case "hours":   return datetime.timedelta(hours=amount)
        case "days":    return datetime.timedelta(days=amount)
        case "weeks":   return datetime.timedelta(weeks=amount)
        case "months":  return datetime.timedelta(days=amount * 30)
        case "years":   return datetime.timedelta(days=amount * 365)
        case _:         raise ValueError(f"Unknown unit: {unit!r}")


def format_duration(amount: int, unit: str) -> str:
    """Return a readable string like '3 Days' or '1 Week'."""
    label = unit.capitalize().rstrip("s") if amount == 1 else unit.capitalize()
    return f"{amount} {label}"

class BanDurationModal(discord.ui.Modal, title="Set Ban Duration"):
    amount_input: discord.ui.TextInput = discord.ui.TextInput(
        label="Duration Amount",
        placeholder="Enter a number, e.g. 7",
        min_length=1,
        max_length=4,
        required=True,
    )

    def __init__(
        self,
        cog: "BanCommand",
        target: discord.Member,
        reason: str,
        delete_messages: int,
        duration_unit: str,
    ) -> None:
        super().__init__()
        self.cog = cog
        self.target = target
        self.reason = reason
        self.delete_messages = delete_messages
        self.duration_unit = duration_unit

    async def on_submit(self, interaction: discord.Interaction) -> None:
        raw = self.amount_input.value.strip()

        if not raw.isdigit() or int(raw) < 1:
            await interaction.response.send_message(
                embed=self.cog._error_embed(
                    "The duration amount must be a positive whole number (e.g. `7`)."
                ),
                ephemeral=True,
            )
            return

        amount = int(raw)

        try:
            delta = resolve_duration(amount, self.duration_unit)
        except ValueError:
            await interaction.response.send_message(
                embed=self.cog._error_embed("Invalid duration unit."),
                ephemeral=True,
            )
            return

        expires_at = datetime.datetime.utcnow() + delta
        delay_seconds = delta.total_seconds()

        duration_label = format_duration(amount, self.duration_unit)
        audit_reason = (
            f"Banned by {interaction.user} ({interaction.user.id}) | "
            f"Duration: {duration_label} | "
            f"Reason: {self.reason}"
        )

        try:
            await self.target.ban(
                reason=audit_reason,
                delete_message_days=self.delete_messages,
            )
        except discord.Forbidden:
            await interaction.response.send_message(
                embed=self.cog._error_embed(
                    "I lack the required permissions to ban this member. "
                    "Please verify my role position and permissions."
                ),
                ephemeral=True,
            )
            return
        except discord.HTTPException as exc:
            await interaction.response.send_message(
                embed=self.cog._error_embed(
                    f"The ban failed due to an API error: `{exc.text}` (code `{exc.code}`)."
                ),
                ephemeral=True,
            )
            return

        self.cog._register_unban_task(
            interaction.guild,
            self.target.id,
            delay_seconds,
            expires_at,
        )

        await interaction.response.send_message(
            embed=self.cog._ban_embed(
                self.target, self.reason, interaction.user, expires_at
            )
        )

class BanCommand(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self._unban_tasks: dict[int, dict[int, asyncio.Task]] = {}

    def _error_embed(self, message: str) -> discord.Embed:
        return discord.Embed(
            title="Action Denied",
            description=message,
            color=discord.Color.from_rgb(200, 60, 60),
            timestamp=datetime.datetime.utcnow(),
        )

    def _ban_embed(
        self,
        target: discord.Member,
        reason: str,
        moderator: discord.Member,
        expires_at: Optional[datetime.datetime],
    ) -> discord.Embed:
        if expires_at is None:
            title = "Member Permanently Banned"
            duration_value = "Permanent"
        else:
            title = "Member Temporarily Banned"
            unix = int(expires_at.timestamp())
            duration_value = f"<t:{unix}:F> (<t:{unix}:R>)"

        embed = discord.Embed(
            title=title,
            description=f"**{target}** (`{target.id}`) has been banned from this server.",
            color=discord.Color.from_rgb(220, 80, 60),
            timestamp=datetime.datetime.utcnow(),
        )
        embed.add_field(name="Reason",                value=reason,            inline=False)
        embed.add_field(name="Ban Expires",           value=duration_value,    inline=True)
        embed.add_field(name="Responsible Moderator", value=moderator.mention, inline=True)
        embed.add_field(name="Target ID",             value=str(target.id),    inline=True)
        embed.set_thumbnail(url=target.display_avatar.url)
        embed.set_footer(text=f"Action performed by {moderator} ({moderator.id})")
        return embed

    def _unban_embed(
        self,
        user: discord.User,
        guild: discord.Guild,
        expires_at: datetime.datetime,
    ) -> discord.Embed:
        embed = discord.Embed(
            title="Temporary Ban Expired — Member Unbanned",
            description=f"**{user}** (`{user.id}`) has been automatically unbanned.",
            color=discord.Color.from_rgb(60, 180, 100),
            timestamp=datetime.datetime.utcnow(),
        )
        embed.add_field(name="Guild",      value=guild.name,                                   inline=True)
        embed.add_field(name="Expired At", value=f"<t:{int(expires_at.timestamp())}:F>",       inline=True)
        embed.set_footer(text="Automatic unban by bot")
        return embed

    async def _schedule_unban(
        self,
        guild: discord.Guild,
        user_id: int,
        delay_seconds: float,
        expires_at: datetime.datetime,
    ) -> None:
        await asyncio.sleep(delay_seconds)
        try:
            user = await self.bot.fetch_user(user_id)
            await guild.unban(user, reason="Temporary ban duration elapsed.")
            channel = guild.system_channel
            if channel and channel.permissions_for(guild.me).send_messages:
                await channel.send(embed=self._unban_embed(user, guild, expires_at))
        except discord.NotFound:
            pass
        except discord.Forbidden:
            pass
        finally:
            self._unban_tasks.get(guild.id, {}).pop(user_id, None)

    def _register_unban_task(
        self,
        guild: discord.Guild,
        user_id: int,
        delay_seconds: float,
        expires_at: datetime.datetime,
    ) -> None:
        existing = self._unban_tasks.get(guild.id, {}).get(user_id)
        if existing and not existing.done():
            existing.cancel()
        task = asyncio.create_task(
            self._schedule_unban(guild, user_id, delay_seconds, expires_at)
        )
        self._unban_tasks.setdefault(guild.id, {})[user_id] = task

    async def _preflight(
        self,
        interaction: discord.Interaction,
        target: discord.Member,
    ) -> bool:
        """
        Run hierarchy and self-ban checks.
        Sends an ephemeral error and returns False if any check fails.
        """
        if target.id == interaction.user.id:
            await interaction.response.send_message(
                embed=self._error_embed("You cannot ban yourself."),
                ephemeral=True,
            )
            return False

        is_owner = interaction.user.id == interaction.guild.owner_id
        if not is_owner and interaction.user.top_role <= target.top_role:
            await interaction.response.send_message(
                embed=self._error_embed(
                    "You cannot ban this member. Their highest role is equal to or "
                    "above your highest role."
                ),
                ephemeral=True,
            )
            return False

        if interaction.guild.me.top_role <= target.top_role:
            await interaction.response.send_message(
                embed=self._error_embed(
                    "I am unable to ban this member. My highest role must be above "
                    "the member's highest role."
                ),
                ephemeral=True,
            )
            return False

        return True

    @app_commands.command(
        name="ban",
        description="Ban a member permanently or for a chosen duration.",
    )
    @app_commands.describe(
        target="The member to ban.",
        reason="Reason for the ban. Stored in the audit log.",
        delete_messages="Number of days of messages to delete (0–7).",
        duration_unit=(
            "Time unit for a temporary ban. "
            "Selecting this opens a popup to enter the amount. "
            "Leave empty for a permanent ban."
        ),
    )
    @app_commands.choices(duration_unit=UNIT_CHOICES)
    @app_commands.default_permissions(ban_members=True)
    async def ban(
        self,
        interaction: discord.Interaction,
        target: discord.Member,
        reason: str = "No reason provided.",
        delete_messages: app_commands.Range[int, 0, 7] = 0,
        duration_unit: Optional[str] = None,
    ) -> None:
        if not await self._preflight(interaction, target):
            return

        if duration_unit is not None:
            modal = BanDurationModal(
                cog=self,
                target=target,
                reason=reason,
                delete_messages=delete_messages,
                duration_unit=duration_unit,
            )
            await interaction.response.send_modal(modal)
            return

        audit_reason = (
            f"Banned by {interaction.user} ({interaction.user.id}) | "
            f"Duration: Permanent | "
            f"Reason: {reason}"
        )

        try:
            await target.ban(
                reason=audit_reason,
                delete_message_days=delete_messages,
            )
        except discord.Forbidden:
            await interaction.response.send_message(
                embed=self._error_embed(
                    "I lack the required permissions to ban this member. "
                    "Please verify my role position and permissions."
                ),
                ephemeral=True,
            )
            return
        except discord.HTTPException as exc:
            await interaction.response.send_message(
                embed=self._error_embed(
                    f"The ban failed due to an API error: `{exc.text}` (code `{exc.code}`)."
                ),
                ephemeral=True,
            )
            return

        await interaction.response.send_message(
            embed=self._ban_embed(target, reason, interaction.user, expires_at=None)
        )

async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(BanCommand(bot))
