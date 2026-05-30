import discord
from discord import app_commands
from discord.ext import commands

class UnbanCommand(commands.Cog):
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

    @app_commands.command(
        name="unban",
        description="Revoke a server ban from a user."
    )
    @app_commands.describe(
        target="The user to unban (you can select them or paste their User ID).",
        reason="The reason for the unban. Stored in the audit log."
    )
    @app_commands.default_permissions(ban_members=True)
    async def unban(
        self,
        interaction: discord.Interaction,
        target: discord.User,
        reason: str = "No reason provided."
    ) -> None:
                
        audit_reason = f"Unbanned by {interaction.user} ({interaction.user.id}) | Reason: {reason}"

        try:
            await interaction.guild.unban(target, reason=audit_reason)
        except discord.NotFound:
            await interaction.response.send_message(
                embed=self._error_embed(
                    f"**{target}** (`{target.id}`) is not currently banned on this server."
                ),
                ephemeral=True,
            )
            return
        except discord.Forbidden:
            await interaction.response.send_message(
                embed=self._error_embed(
                    "I lack the `Ban Members` permission required to unban users."
                ),
                ephemeral=True,
            )
            return
        except discord.HTTPException as exc:
            await interaction.response.send_message(
                embed=self._error_embed(
                    f"API Error: `{exc.text}` (code `{exc.code}`)."
                ),
                ephemeral=True,
            )
            return

        await interaction.response.send_message(
            embed=self._success_embed(
                title="User Unbanned",
                description=f"Successfully removed the ban for **{target}** (`{target.id}`).",
                moderator=interaction.user
            )
        )

async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(UnbanCommand(bot))