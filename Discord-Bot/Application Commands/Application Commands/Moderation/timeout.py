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
]

def resolve_duration(amount: int, unit: str) -> datetime.timedelta:
    """Convert amount + unit into a timedelta."""
    match unit.lower():
        case "minutes": return datetime.timedelta(minutes=amount)
        case "hours":   return datetime.timedelta(hours=amount)
        case "days":    return datetime.timedelta(days=amount)
        case "weeks":   return datetime.timedelta(weeks=amount)
        case _:         raise ValueError(f"Unknown unit: {unit!r}")

def format_duration(amount: int, unit: str) -> str:
    """Return a readable string like '3 Days' or '1 Week'."""
    label = unit.capitalize().rstrip("s") if amount == 1 else unit.capitalize()
    return f"{amount} {label}"

class TimeoutDurationModal(discord.ui.Modal, title="Set Timeout Duration"):
    amount_input: discord.ui.TextInput = discord.ui.TextInput(
        label="Duration Amount",
        placeholder="Enter a number, e.g. 7",
        min_length=1,
        max_length=4,
        required=True,
    )

    def __init__(
        self,
        cog: "TimeoutCommand",
        target: discord.Member,
        reason: str,
        duration_unit: str,
    ) -> None:
        super().__init__()
        self.cog = cog
        self.target = target
        self.reason = reason
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

        if delta.total_seconds() > 2419200:
            await interaction.response.send_message(
                embed=self.cog._error_embed(
                    "Discord limits timeouts to a maximum of 28 days."
                ),
                ephemeral=True,
            )
            return

        expires_at = discord.utils.utcnow() + delta
        duration_label = format_duration(amount, self.duration_unit)
        
        audit_reason = (
            f"Timed out by {interaction.user} ({interaction.user.id}) | "
            f"Duration: {duration_label} | "
            f"Reason: {self.reason}"
        )

        try:
            await self.target.timeout(expires_at, reason=audit_reason)
        except discord.Forbidden:
            await interaction.response.send_message(
                embed=self.cog._error_embed(
                    "I lack the required permissions to timeout this member. "
                    "Please verify my role position and permissions."
                ),
                ephemeral=True,
            )
            return
        except discord.HTTPException as exc:
            await interaction.response.send_message(
                embed=self.cog._error_embed(
                    f"The timeout failed due to an API error: `{exc.text}` (code `{exc.code}`)."
                ),
                ephemeral=True,
            )
            return

        await interaction.response.send_message(
            embed=self.cog._timeout_embed(
                self.target, self.reason, interaction.user, expires_at
            )
        )

class TimeoutCommand(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    def _error_embed(self, message: str) -> discord.Embed:
        """Returns a standardised error embed."""
        return discord.Embed(
            title="Action Denied",
            description=message,
            color=discord.Color.from_rgb(200, 60, 60),
            timestamp=discord.utils.utcnow(),
        )

    def _timeout_embed(
        self,
        target: discord.Member,
        reason: str,
        moderator: discord.Member,
        expires_at: datetime.datetime,
    ) -> discord.Embed:
        """Returns a timeout-confirmation embed."""
        unix = int(expires_at.timestamp())
        duration_value = f"<t:{unix}:F> (<t:{unix}:R>)"

        embed = discord.Embed(
            title="Member Timed Out",
            description=f"**{target}** (`{target.id}`) has been timed out.",
            color=discord.Color.from_rgb(100, 140, 210),
            timestamp=discord.utils.utcnow(),
        )
        embed.add_field(name="Reason",                value=reason,         inline=False)
        embed.add_field(name="Timeout Expires",       value=duration_value, inline=True)
        embed.add_field(name="Responsible Moderator", value=moderator.mention, inline=True)
        embed.add_field(name="Target ID",             value=str(target.id),    inline=True)
        embed.set_thumbnail(url=target.display_avatar.url)
        embed.set_footer(text=f"Action performed by {moderator} ({moderator.id})")
        return embed

    def _untimeout_embed(
        self,
        target: discord.Member,
        reason: str,
        moderator: discord.Member,
    ) -> discord.Embed:
        """Returns an untimeout-confirmation embed."""
        embed = discord.Embed(
            title="Timeout Removed",
            description=f"The timeout for **{target}** (`{target.id}`) has been removed.",
            color=discord.Color.from_rgb(60, 180, 100),
            timestamp=discord.utils.utcnow(),
        )
        embed.add_field(name="Reason",                value=reason,         inline=False)
        embed.add_field(name="Responsible Moderator", value=moderator.mention, inline=True)
        embed.add_field(name="Target ID",             value=str(target.id),    inline=True)
        embed.set_thumbnail(url=target.display_avatar.url)
        embed.set_footer(text=f"Action performed by {moderator} ({moderator.id})")
        return embed

    async def _preflight(
        self,
        interaction: discord.Interaction,
        target: discord.Member,
    ) -> bool:
        """
        Run self-targeting, executor hierarchy, and bot hierarchy checks.
        Sends an ephemeral error and returns False if any check fails.
        """
        if target.id == interaction.user.id:
            await interaction.response.send_message(
                embed=self._error_embed("You cannot target yourself."),
                ephemeral=True,
            )
            return False

        is_owner = interaction.user.id == interaction.guild.owner_id
        if not is_owner and interaction.user.top_role <= target.top_role:
            await interaction.response.send_message(
                embed=self._error_embed(
                    "You cannot moderate this member. Their highest role is equal to or "
                    "above your highest role."
                ),
                ephemeral=True,
            )
            return False

        if interaction.guild.me.top_role <= target.top_role:
            await interaction.response.send_message(
                embed=self._error_embed(
                    "I am unable to moderate this member. My highest role must be above "
                    "the member's highest role."
                ),
                ephemeral=True,
            )
            return False

        return True

    @app_commands.command(
        name="timeout",
        description="Restrict a member from sending messages and joining voice channels.",
    )
    @app_commands.describe(
        target="The member to timeout.",
        duration_unit="Time unit for the timeout. Opens a popup to enter the amount.",
        reason="Reason for the timeout. Stored in the audit log.",
    )
    @app_commands.choices(duration_unit=UNIT_CHOICES)
    @app_commands.default_permissions(moderate_members=True)
    async def timeout(
        self,
        interaction: discord.Interaction,
        target: discord.Member,
        duration_unit: str,
        reason: str = "No reason provided.",
    ) -> None:
        if not await self._preflight(interaction, target):
            return
            
        if target.is_timed_out():
            await interaction.response.send_message(
                embed=self._error_embed(
                    "This member is already timed out. Use `/untimeout` first or wait for it to expire."
                ),
                ephemeral=True,
            )
            return

        modal = TimeoutDurationModal(
            cog=self,
            target=target,
            reason=reason,
            duration_unit=duration_unit,
        )
        await interaction.response.send_modal(modal)

    @app_commands.command(
        name="untimeout",
        description="Remove an active timeout from a member.",
    )
    @app_commands.describe(
        target="The member to untimeout.",
        reason="Reason for removing the timeout.",
    )
    @app_commands.default_permissions(moderate_members=True)
    async def untimeout(
        self,
        interaction: discord.Interaction,
        target: discord.Member,
        reason: str = "No reason provided.",
    ) -> None:
        if not await self._preflight(interaction, target):
            return

        if not target.is_timed_out():
            await interaction.response.send_message(
                embed=self._error_embed("This member is not currently timed out."),
                ephemeral=True,
            )
            return

        audit_reason = (
            f"Timeout removed by {interaction.user} ({interaction.user.id}) | "
            f"Reason: {reason}"
        )

        try:
            await target.timeout(None, reason=audit_reason)
        except discord.Forbidden:
            await interaction.response.send_message(
                embed=self._error_embed(
                    "I lack the required permissions to untimeout this member."
                ),
                ephemeral=True,
            )
            return
        except discord.HTTPException as exc:
            await interaction.response.send_message(
                embed=self._error_embed(
                    f"The action failed due to an API error: `{exc.text}` (code `{exc.code}`)."
                ),
                ephemeral=True,
            )
            return

        await interaction.response.send_message(
            embed=self._untimeout_embed(target, reason, interaction.user)
        )

async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(TimeoutCommand(bot))