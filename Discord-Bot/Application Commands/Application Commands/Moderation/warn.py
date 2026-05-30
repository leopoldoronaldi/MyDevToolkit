import discord
from discord import app_commands
from discord.ext import commands

class WarningSystem(commands.Cog):
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
        Run self-targeting, bot-targeting, and executor hierarchy checks.
        """
        if target.id == interaction.user.id:
            await interaction.response.send_message(
                embed=self._error_embed("You cannot warn yourself."),
                ephemeral=True,
            )
            return False
            
        if target.bot:
            await interaction.response.send_message(
                embed=self._error_embed("You cannot issue warnings to bots."),
                ephemeral=True,
            )
            return False

        is_owner = interaction.user.id == interaction.guild.owner_id
        if not is_owner and interaction.user.top_role <= target.top_role:
            await interaction.response.send_message(
                embed=self._error_embed(
                    "You cannot warn this member. Their highest role is equal to or "
                    "above your highest role."
                ),
                ephemeral=True,
            )
            return False

        return True

    @app_commands.command(
        name="warn",
        description="Issue a formal warning to a member."
    )
    @app_commands.describe(
        target="The member to warn.",
        reason="The reason for the warning. This will be sent to the user."
    )
    @app_commands.default_permissions(moderate_members=True)
    async def warn(
        self,
        interaction: discord.Interaction,
        target: discord.Member,
        reason: str
    ) -> None:
        if not await self._preflight(interaction, target):
            return

        dm_embed = discord.Embed(
            title=f"Warning Received in {interaction.guild.name}",
            description="You have received a formal warning from the moderation team.",
            color=discord.Color.from_rgb(220, 150, 40),
            timestamp=discord.utils.utcnow()
        )
        dm_embed.add_field(name="Reason", value=reason, inline=False)
        
        if interaction.guild.icon:
            dm_embed.set_thumbnail(url=interaction.guild.icon.url)

        dm_sent = True
        try:
            await target.send(embed=dm_embed)
        except discord.Forbidden:
            dm_sent = False
        status_msg = f"Successfully recorded warning for {target.mention}."
        if not dm_sent:
            status_msg += "\n*Note: The user could not be notified because their DMs are disabled.*"

        await interaction.response.send_message(
            embed=self._success_embed(
                title="Member Warned",
                description=f"{status_msg}\n\n**Reason:** {reason}",
                moderator=interaction.user
            )
        )

async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(WarningSystem(bot))