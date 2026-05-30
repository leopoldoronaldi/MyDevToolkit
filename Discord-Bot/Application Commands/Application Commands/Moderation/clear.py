from typing import Optional

import discord
from discord import app_commands
from discord.ext import commands

class MessageManagement(commands.Cog):
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
        Verify if the bot has the required permissions to manage messages in the target channel.
        """
        me = interaction.guild.me
        permissions = channel.permissions_for(me)
        
        if not permissions.manage_messages or not permissions.read_message_history:
            # Utilizing followup because this command will be deferred immediately upon execution
            await interaction.followup.send(
                embed=self._error_embed(
                    f"I lack the `Manage Messages` and/or `Read Message History` permission in {channel.mention}."
                ),
                ephemeral=True,
            )
            return False
        return True

    @app_commands.command(
        name="clear",
        description="Bulk delete messages in the current channel."
    )
    @app_commands.describe(
        amount="The number of messages to scan and delete (1-100).",
        target="Optional: Only delete messages from this specific user."
    )
    @app_commands.default_permissions(manage_messages=True)
    async def clear(
        self,
        interaction: discord.Interaction,
        amount: app_commands.Range[int, 1, 100],
        target: Optional[discord.Member] = None
    ) -> None:
        
        # 1. IMMEDIATE DEFERRAL
        # Bulk deletion can take several seconds. We must defer to extend the 3-second timeout limit.
        # ephemeral=True ensures the "Bot is thinking..." message is only visible to the moderator.
        await interaction.response.defer(ephemeral=True)

        channel = interaction.channel

        if not isinstance(channel, (discord.TextChannel, discord.VoiceChannel, discord.Thread)):
            await interaction.followup.send(
                embed=self._error_embed("This command can only be used in text-based channels."),
                ephemeral=True
            )
            return

        if not await self._preflight_bot_permissions(interaction, channel):
            return

        audit_reason = f"Bulk delete invoked by {interaction.user} ({interaction.user.id})"

        # 2. TARGET FILTER LOGIC
        def check_target(message: discord.Message) -> bool:
            if target:
                return message.author.id == target.id
            return True

        # 3. EXECUTE PURGE
        try:
            # Discord API limitation: bulk delete only works on messages newer than 14 days.
            # The purge method handles this automatically by falling back to single deletion 
            # for older messages, but it is limited by our scan limit (amount).
            deleted = await channel.purge(limit=amount, check=check_target, reason=audit_reason)
        except discord.Forbidden:
            await interaction.followup.send(
                embed=self._error_embed("I do not have permissions to delete messages here."),
                ephemeral=True
            )
            return
        except discord.HTTPException as exc:
            await interaction.followup.send(
                embed=self._error_embed(f"API Error during deletion: `{exc.text}`"),
                ephemeral=True
            )
            return

        # 4. SUCCESS RESPONSE
        if target:
            description = f"Successfully deleted **{len(deleted)}** messages from **{target}**."
        else:
            description = f"Successfully deleted **{len(deleted)}** messages."

        # Since we deferred earlier, we MUST use interaction.followup.send
        await interaction.followup.send(
            embed=self._success_embed(
                title="Messages Cleared",
                description=description,
                moderator=interaction.user
            ),
            ephemeral=True
        )

async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(MessageManagement(bot))