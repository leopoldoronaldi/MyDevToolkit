import datetime

import discord
from discord import app_commands
from discord.ext import commands

class KickCommand(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    def _error_embed(self, message: str) -> discord.Embed:
        """Returns a standardised error embed."""
        return discord.Embed(
            title="Action Denied",
            description=message,
            color=discord.Color.from_rgb(200, 60, 60),
            timestamp=datetime.datetime.utcnow(),
        )

    def _kick_embed(
        self,
        target: discord.Member,
        reason: str,
        moderator: discord.Member,
    ) -> discord.Embed:
        """Returns a kick-confirmation embed."""
        embed = discord.Embed(
            title="Member Kicked",
            description=(
                f"**{target}** (`{target.id}`) has been kicked from this server."
            ),
            color=discord.Color.from_rgb(210, 140, 40),
            timestamp=datetime.datetime.utcnow(),
        )
        embed.add_field(name="Reason",                value=reason,            inline=False)
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
        Run self-kick, executor hierarchy, and bot hierarchy checks.
        Sends an ephemeral error and returns False if any check fails.
        """

        if target.id == interaction.user.id:
            await interaction.response.send_message(
                embed=self._error_embed("You cannot kick yourself."),
                ephemeral=True,
            )
            return False

        is_owner = interaction.user.id == interaction.guild.owner_id
        if not is_owner and interaction.user.top_role <= target.top_role:
            await interaction.response.send_message(
                embed=self._error_embed(
                    "You cannot kick this member. Their highest role is equal to or "
                    "above your highest role."
                ),
                ephemeral=True,
            )
            return False

        if interaction.guild.me.top_role <= target.top_role:
            await interaction.response.send_message(
                embed=self._error_embed(
                    "I am unable to kick this member. My highest role must be above "
                    "the member's highest role."
                ),
                ephemeral=True,
            )
            return False

        return True

    @app_commands.command(
        name="kick",
        description="Kick a member from this server.",
    )
    @app_commands.describe(
        target="The member to kick.",
        reason="Reason for the kick. Stored in the audit log.",
    )
    @app_commands.default_permissions(kick_members=True)
    async def kick(
        self,
        interaction: discord.Interaction,
        target: discord.Member,
        reason: str = "No reason provided.",
    ) -> None:
        """
        Kicks a member from the guild with full hierarchy validation,
        an informative public embed, and a complete audit-log entry.
        """

        if not await self._preflight(interaction, target):
            return

        audit_reason = (
            f"Kicked by {interaction.user} ({interaction.user.id}) | "
            f"Reason: {reason}"
        )

        try:
            await target.kick(reason=audit_reason)
        except discord.Forbidden:
            await interaction.response.send_message(
                embed=self._error_embed(
                    "I lack the required permissions to kick this member. "
                    "Please verify my role position and permissions."
                ),
                ephemeral=True,
            )
            return
        except discord.HTTPException as exc:
            await interaction.response.send_message(
                embed=self._error_embed(
                    f"The kick failed due to an API error: `{exc.text}` (code `{exc.code}`)."
                ),
                ephemeral=True,
            )
            return

        await interaction.response.send_message(
            embed=self._kick_embed(target, reason, interaction.user)
        )

async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(KickCommand(bot))