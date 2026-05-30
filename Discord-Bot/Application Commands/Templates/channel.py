from typing import Optional

import discord
from discord import app_commands
from discord.ext import commands

class ChannelManagement(commands.Cog):
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
        moderator: discord.Member
    ) -> discord.Embed:
        """Returns a standardised success embed."""
        embed = discord.Embed(
            title=title,
            description=description,
            color=discord.Color.from_rgb(60, 180, 100),
            timestamp=discord.utils.utcnow(),
        )
        embed.set_footer(text=f"Action performed by {moderator} ({moderator.id})")
        return embed

    async def _preflight_bot_permissions(
        self, 
        interaction: discord.Interaction, 
        channel: discord.abc.GuildChannel
    ) -> bool:
        """
        Verify if the bot has the required permissions to modify the target channel.
        """
        me = interaction.guild.me
        permissions = channel.permissions_for(me)
        
        if not permissions.manage_channels:
            await interaction.response.send_message(
                embed=self._error_embed(
                    f"I lack the `Manage Channels` permission in {channel.mention}."
                ),
                ephemeral=True,
            )
            return False
        return True

    channel_group = app_commands.Group(
        name="channel",
        description="Channel management and configuration commands.",
        default_permissions=discord.Permissions(manage_channels=True)
    )

    @channel_group.command(name="rename", description="Rename a text or voice channel.")
    @app_commands.describe(
        new_name="The new name for the channel (1-100 characters).",
        target_channel="The channel to rename. Defaults to the current channel."
    )
    async def rename_channel(
        self, 
        interaction: discord.Interaction, 
        new_name: app_commands.Range[str, 1, 100], 
        target_channel: Optional[discord.abc.GuildChannel] = None
    ) -> None:
        channel = target_channel or interaction.channel

        if not await self._preflight_bot_permissions(interaction, channel):
            return

        audit_reason = f"Channel renamed by {interaction.user} ({interaction.user.id})"
        old_name = channel.name

        try:
            await channel.edit(name=new_name, reason=audit_reason)
        except discord.HTTPException as exc:
            await interaction.response.send_message(
                embed=self._error_embed(f"API Error (Possible Rate Limit): `{exc.text}`"),
                ephemeral=True,
            )
            return

        await interaction.response.send_message(
            embed=self._success_embed(
                title="Channel Renamed",
                description=f"Successfully renamed **#{old_name}** to {channel.mention}.",
                moderator=interaction.user
            )
        )

    @channel_group.command(name="topic", description="Set or clear the topic of a text channel.")
    @app_commands.describe(
        new_topic="The new topic (max 1024 characters). Leave empty to clear.",
        target_channel="The text channel to modify. Defaults to the current channel."
    )
    async def set_topic(
        self, 
        interaction: discord.Interaction, 
        new_topic: Optional[app_commands.Range[str, 1, 1024]] = None,
        target_channel: Optional[discord.TextChannel] = None
    ) -> None:
        channel = target_channel or interaction.channel

        if not isinstance(channel, discord.TextChannel):
            await interaction.response.send_message(
                embed=self._error_embed("Topics can only be set on Text Channels."),
                ephemeral=True,
            )
            return

        if not await self._preflight_bot_permissions(interaction, channel):
            return

        audit_reason = f"Topic modified by {interaction.user} ({interaction.user.id})"
        
        try:
            await channel.edit(topic=new_topic, reason=audit_reason)
        except discord.HTTPException as exc:
            await interaction.response.send_message(
                embed=self._error_embed(f"API Error: `{exc.text}`"),
                ephemeral=True,
            )
            return

        status = f"updated to:\n```{new_topic}```" if new_topic else "cleared."
        
        await interaction.response.send_message(
            embed=self._success_embed(
                title="Channel Topic Updated",
                description=f"The topic for {channel.mention} has been {status}",
                moderator=interaction.user
            )
        )

    @channel_group.command(name="slowmode", description="Set the slowmode delay for a text channel.")
    @app_commands.describe(
        seconds="Slowmode delay in seconds (0 to disable, max 21600).",
        target_channel="The text channel to modify. Defaults to the current channel."
    )
    async def set_slowmode(
        self, 
        interaction: discord.Interaction, 
        seconds: app_commands.Range[int, 0, 21600],
        target_channel: Optional[discord.TextChannel] = None
    ) -> None:
        channel = target_channel or interaction.channel

        if not isinstance(channel, discord.TextChannel):
            await interaction.response.send_message(
                embed=self._error_embed("Slowmode can only be applied to Text Channels."),
                ephemeral=True,
            )
            return

        if not await self._preflight_bot_permissions(interaction, channel):
            return

        audit_reason = f"Slowmode adjusted by {interaction.user} ({interaction.user.id})"

        try:
            await channel.edit(slowmode_delay=seconds, reason=audit_reason)
        except discord.HTTPException as exc:
            await interaction.response.send_message(
                embed=self._error_embed(f"API Error: `{exc.text}`"),
                ephemeral=True,
            )
            return

        status = f"set to **{seconds} seconds**" if seconds > 0 else "disabled"

        await interaction.response.send_message(
            embed=self._success_embed(
                title="Slowmode Updated",
                description=f"Slowmode for {channel.mention} has been {status}.",
                moderator=interaction.user
            )
        )

    @channel_group.command(name="nsfw", description="Toggle the Age-Restricted (NSFW) status of a channel.")
    @app_commands.describe(
        enabled="True to enable Age-Restriction, False to disable.",
        target_channel="The channel to modify. Defaults to the current channel."
    )
    async def toggle_nsfw(
        self, 
        interaction: discord.Interaction, 
        enabled: bool,
        target_channel: Optional[discord.TextChannel] = None
    ) -> None:
        channel = target_channel or interaction.channel

        if not isinstance(channel, discord.TextChannel):
            await interaction.response.send_message(
                embed=self._error_embed("Age-Restriction (NSFW) can only be toggled on Text Channels."),
                ephemeral=True,
            )
            return

        if not await self._preflight_bot_permissions(interaction, channel):
            return

        if channel.nsfw == enabled:
            await interaction.response.send_message(
                embed=self._error_embed(f"This channel's Age-Restriction is already set to `{enabled}`."),
                ephemeral=True,
            )
            return

        audit_reason = f"Age-Restriction toggled by {interaction.user} ({interaction.user.id})"

        try:
            await channel.edit(nsfw=enabled, reason=audit_reason)
        except discord.HTTPException as exc:
            await interaction.response.send_message(
                embed=self._error_embed(f"API Error: `{exc.text}`"),
                ephemeral=True,
            )
            return

        status = "enabled" if enabled else "disabled"

        await interaction.response.send_message(
            embed=self._success_embed(
                title="Age-Restriction Updated",
                description=f"Age-Restriction for {channel.mention} has been {status}.",
                moderator=interaction.user
            )
        )

async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(ChannelManagement(bot))