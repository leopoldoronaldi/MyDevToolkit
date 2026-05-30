from typing import Optional

import discord
from discord import app_commands
from discord.ext import commands

class ChannelLockdown(commands.Cog):
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

    def _success_embed(
        self, 
        title: str, 
        description: str, 
        moderator: discord.Member,
        color: discord.Color
    ) -> discord.Embed:
        """Returns a standardised success embed."""
        embed = discord.Embed(
            title=title,
            description=description,
            color=color,
            timestamp=discord.utils.utcnow(),
        )
        embed.set_footer(text=f"Action performed by {moderator} ({moderator.id})")
        return embed

    async def _preflight_bot_permissions(
        self, 
        interaction: discord.Interaction, 
        channel: discord.TextChannel
    ) -> bool:
        """
        Verify if the bot has the required permissions to manage channel roles/permissions.
        """
        me = interaction.guild.me
        permissions = channel.permissions_for(me)
        
        if not permissions.manage_roles:
            await interaction.response.send_message(
                embed=self._error_embed(
                    f"I lack the `Manage Roles/Permissions` permission in {channel.mention}."
                ),
                ephemeral=True,
            )
            return False
        return True

    @app_commands.command(
        name="lock",
        description="Lock the channel, preventing default members from sending messages."
    )
    @app_commands.describe(
        target_channel="The channel to lock. Defaults to the current channel.",
        reason="The reason for the lockdown."
    )
    @app_commands.default_permissions(manage_channels=True)
    async def lock_channel(
        self,
        interaction: discord.Interaction,
        target_channel: Optional[discord.TextChannel] = None,
        reason: str = "Emergency lockdown."
    ) -> None:
        channel = target_channel or interaction.channel

        if not isinstance(channel, discord.TextChannel):
            await interaction.response.send_message(
                embed=self._error_embed("Lockdown can only be applied to text channels."),
                ephemeral=True
            )
            return

        if not await self._preflight_bot_permissions(interaction, channel):
            return

        default_role = interaction.guild.default_role
        current_overwrite = channel.overwrites_for(default_role)

        if current_overwrite.send_messages is False:
            await interaction.response.send_message(
                embed=self._error_embed(f"{channel.mention} is already locked."),
                ephemeral=True
            )
            return

        current_overwrite.send_messages = False
        audit_reason = f"Channel locked by {interaction.user} | Reason: {reason}"

        try:
            await channel.set_permissions(default_role, overwrite=current_overwrite, reason=audit_reason)
        except discord.HTTPException as exc:
            await interaction.response.send_message(
                embed=self._error_embed(f"API Error: `{exc.text}`"),
                ephemeral=True
            )
            return

        await interaction.response.send_message(
            embed=self._success_embed(
                title="Channel Locked",
                description=f"{channel.mention} has been locked.\n**Reason:** {reason}",
                moderator=interaction.user,
                color=discord.Color.from_rgb(220, 80, 60)
            )
        )

    @app_commands.command(
        name="unlock",
        description="Unlock the channel, restoring default messaging permissions."
    )
    @app_commands.describe(
        target_channel="The channel to unlock. Defaults to the current channel."
    )
    @app_commands.default_permissions(manage_channels=True)
    async def unlock_channel(
        self,
        interaction: discord.Interaction,
        target_channel: Optional[discord.TextChannel] = None
    ) -> None:
        channel = target_channel or interaction.channel

        if not isinstance(channel, discord.TextChannel):
            await interaction.response.send_message(
                embed=self._error_embed("Unlock can only be applied to text channels."),
                ephemeral=True
            )
            return

        if not await self._preflight_bot_permissions(interaction, channel):
            return

        default_role = interaction.guild.default_role
        current_overwrite = channel.overwrites_for(default_role)

        if current_overwrite.send_messages is not False:
            await interaction.response.send_message(
                embed=self._error_embed(f"{channel.mention} is not currently locked."),
                ephemeral=True
            )
            return

        current_overwrite.send_messages = None
        audit_reason = f"Channel unlocked by {interaction.user}"

        try:
            await channel.set_permissions(default_role, overwrite=current_overwrite, reason=audit_reason)
        except discord.HTTPException as exc:
            await interaction.response.send_message(
                embed=self._error_embed(f"API Error: `{exc.text}`"),
                ephemeral=True
            )
            return

        await interaction.response.send_message(
            embed=self._success_embed(
                title="Channel Unlocked",
                description=f"{channel.mention} has been unlocked. Standard permissions restored.",
                moderator=interaction.user,
                color=discord.Color.from_rgb(60, 180, 100)
            )
        )

async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(ChannelLockdown(bot))