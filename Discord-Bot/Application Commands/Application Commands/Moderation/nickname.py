from typing import Optional

import discord
from discord import app_commands
from discord.ext import commands

class NicknameManagement(commands.Cog):
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

    async def _preflight(
        self,
        interaction: discord.Interaction,
        target: discord.Member,
    ) -> bool:
        """
        Run hierarchy and API limitation checks for nickname management.
        """
        if target.id == interaction.guild.owner_id:
            await interaction.response.send_message(
                embed=self._error_embed(
                    "Discord API limitation: The server owner's nickname cannot be modified by bots."
                ),
                ephemeral=True,
            )
            return False

        is_owner = interaction.user.id == interaction.guild.owner_id

        if not is_owner and interaction.user.top_role <= target.top_role:
            await interaction.response.send_message(
                embed=self._error_embed(
                    "You cannot change this member's nickname. Their highest role is equal to or "
                    "above your highest role."
                ),
                ephemeral=True,
            )
            return False

        if interaction.guild.me.top_role <= target.top_role:
            await interaction.response.send_message(
                embed=self._error_embed(
                    "I am unable to modify this member's nickname. My highest role must be above "
                    "the member's highest role."
                ),
                ephemeral=True,
            )
            return False

        return True

    @app_commands.command(
        name="nickname",
        description="Change or reset a member's nickname."
    )
    @app_commands.describe(
        target="The member whose nickname you want to change.",
        new_nickname="The new nickname (max 32 chars). Leave empty to reset to their default username."
    )
    @app_commands.default_permissions(manage_nicknames=True)
    async def set_nickname(
        self,
        interaction: discord.Interaction,
        target: discord.Member,
        new_nickname: Optional[app_commands.Range[str, 1, 32]] = None
    ) -> None:
        
        if target.id != interaction.user.id and not await self._preflight(interaction, target):
            return

        audit_reason = f"Nickname modified by {interaction.user} ({interaction.user.id})"

        try:
            await target.edit(nick=new_nickname, reason=audit_reason)
        except discord.Forbidden:
            await interaction.response.send_message(
                embed=self._error_embed("I lack the `Manage Nicknames` permission."),
                ephemeral=True,
            )
            return
        except discord.HTTPException as exc:
            await interaction.response.send_message(
                embed=self._error_embed(f"API Error: `{exc.text}` (code `{exc.code}`)."),
                ephemeral=True,
            )
            return

        if new_nickname:
            description = f"Successfully changed the nickname of **{target.name}** to `{new_nickname}`."
        else:
            description = f"Successfully reset the nickname for **{target.name}**."

        await interaction.response.send_message(
            embed=self._success_embed(
                title="Nickname Updated",
                description=description,
                moderator=interaction.user
            )
        )

async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(NicknameManagement(bot))