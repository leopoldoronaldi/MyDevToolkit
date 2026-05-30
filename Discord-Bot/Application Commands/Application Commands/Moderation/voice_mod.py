import discord
from discord import app_commands
from discord.ext import commands

class VoiceModeration(commands.Cog):
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

    async def _preflight_voice(
        self,
        interaction: discord.Interaction,
        target: discord.Member,
    ) -> bool:
        """
        Run hierarchy checks and verify if the target is actually connected to a voice channel.
        """
        if target.id == interaction.user.id:
            await interaction.response.send_message(
                embed=self._error_embed("You cannot execute voice moderation actions on yourself."),
                ephemeral=True,
            )
            return False

        if not target.voice or not target.voice.channel:
            await interaction.response.send_message(
                embed=self._error_embed(f"**{target.display_name}** is not currently connected to any voice channel."),
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

    voice_group = app_commands.Group(
        name="voice",
        description="Voice channel moderation commands.",
        default_permissions=discord.Permissions(mute_members=True, deafen_members=True, move_members=True)
    )

    @voice_group.command(name="mute", description="Server-mute a member in a voice channel.")
    @app_commands.describe(
        target="The member to mute.",
        reason="The reason for the mute. Stored in the audit log."
    )
    async def voice_mute(
        self, 
        interaction: discord.Interaction, 
        target: discord.Member, 
        reason: str = "No reason provided."
    ) -> None:
        if not await self._preflight_voice(interaction, target):
            return

        if target.voice.mute:
            await interaction.response.send_message(
                embed=self._error_embed(f"**{target.display_name}** is already server-muted."),
                ephemeral=True
            )
            return

        audit_reason = f"Voice Mute by {interaction.user} ({interaction.user.id}) | Reason: {reason}"

        try:
            await target.edit(mute=True, reason=audit_reason)
        except discord.Forbidden:
            await interaction.response.send_message(
                embed=self._error_embed("I lack the `Mute Members` permission."),
                ephemeral=True,
            )
            return
        except discord.HTTPException as exc:
            await interaction.response.send_message(
                embed=self._error_embed(f"API Error: `{exc.text}` (code `{exc.code}`)."),
                ephemeral=True,
            )
            return

        await interaction.response.send_message(
            embed=self._success_embed(
                title="Member Voice-Muted",
                description=f"Successfully server-muted {target.mention} in {target.voice.channel.mention}.",
                moderator=interaction.user
            )
        )

    @voice_group.command(name="unmute", description="Remove a server-mute from a member.")
    @app_commands.describe(target="The member to unmute.")
    async def voice_unmute(
        self, 
        interaction: discord.Interaction, 
        target: discord.Member
    ) -> None:
        if not await self._preflight_voice(interaction, target):
            return

        if not target.voice.mute:
            await interaction.response.send_message(
                embed=self._error_embed(f"**{target.display_name}** is not server-muted."),
                ephemeral=True
            )
            return

        audit_reason = f"Voice Unmute by {interaction.user} ({interaction.user.id})"

        try:
            await target.edit(mute=False, reason=audit_reason)
        except discord.HTTPException as exc:
            await interaction.response.send_message(
                embed=self._error_embed(f"API Error: `{exc.text}`"),
                ephemeral=True,
            )
            return

        await interaction.response.send_message(
            embed=self._success_embed(
                title="Member Voice-Unmuted",
                description=f"Successfully removed the server-mute from {target.mention}.",
                moderator=interaction.user
            )
        )

    @voice_group.command(name="deafen", description="Server-deafen a member in a voice channel.")
    @app_commands.describe(
        target="The member to deafen.",
        reason="The reason for the deafen. Stored in the audit log."
    )
    async def voice_deafen(
        self, 
        interaction: discord.Interaction, 
        target: discord.Member, 
        reason: str = "No reason provided."
    ) -> None:
        if not await self._preflight_voice(interaction, target):
            return

        if target.voice.deaf:
            await interaction.response.send_message(
                embed=self._error_embed(f"**{target.display_name}** is already server-deafened."),
                ephemeral=True
            )
            return

        audit_reason = f"Voice Deafen by {interaction.user} ({interaction.user.id}) | Reason: {reason}"

        try:
            await target.edit(deafen=True, reason=audit_reason)
        except discord.Forbidden:
            await interaction.response.send_message(
                embed=self._error_embed("I lack the `Deafen Members` permission."),
                ephemeral=True,
            )
            return
        except discord.HTTPException as exc:
            await interaction.response.send_message(
                embed=self._error_embed(f"API Error: `{exc.text}`"),
                ephemeral=True,
            )
            return

        await interaction.response.send_message(
            embed=self._success_embed(
                title="Member Voice-Deafened",
                description=f"Successfully server-deafened {target.mention} in {target.voice.channel.mention}.",
                moderator=interaction.user
            )
        )

    @voice_group.command(name="undeafen", description="Remove a server-deafen from a member.")
    @app_commands.describe(target="The member to undeafen.")
    async def voice_undeafen(
        self, 
        interaction: discord.Interaction, 
        target: discord.Member
    ) -> None:
        if not await self._preflight_voice(interaction, target):
            return

        if not target.voice.deaf:
            await interaction.response.send_message(
                embed=self._error_embed(f"**{target.display_name}** is not server-deafened."),
                ephemeral=True
            )
            return

        audit_reason = f"Voice Undeafen by {interaction.user} ({interaction.user.id})"

        try:
            await target.edit(deafen=False, reason=audit_reason)
        except discord.HTTPException as exc:
            await interaction.response.send_message(
                embed=self._error_embed(f"API Error: `{exc.text}`"),
                ephemeral=True,
            )
            return

        await interaction.response.send_message(
            embed=self._success_embed(
                title="Member Voice-Undeafened",
                description=f"Successfully removed the server-deafen from {target.mention}.",
                moderator=interaction.user
            )
        )

    @voice_group.command(name="kick", description="Disconnect a member from their current voice channel.")
    @app_commands.describe(
        target="The member to disconnect.",
        reason="The reason for the disconnect. Stored in the audit log."
    )
    async def voice_kick(
        self, 
        interaction: discord.Interaction, 
        target: discord.Member, 
        reason: str = "No reason provided."
    ) -> None:
        if not await self._preflight_voice(interaction, target):
            return

        channel_name = target.voice.channel.name
        audit_reason = f"Voice Kick by {interaction.user} ({interaction.user.id}) | Reason: {reason}"

        try:
            await target.move_to(None, reason=audit_reason)
        except discord.Forbidden:
            await interaction.response.send_message(
                embed=self._error_embed("I lack the `Move Members` permission required to disconnect users."),
                ephemeral=True,
            )
            return
        except discord.HTTPException as exc:
            await interaction.response.send_message(
                embed=self._error_embed(f"API Error: `{exc.text}`"),
                ephemeral=True,
            )
            return

        await interaction.response.send_message(
            embed=self._success_embed(
                title="Member Disconnected",
                description=f"Successfully disconnected {target.mention} from **{channel_name}**.",
                moderator=interaction.user
            )
        )

async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(VoiceModeration(bot))