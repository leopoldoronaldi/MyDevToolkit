import discord
from discord import app_commands
from discord.ext import commands

class RoleManagement(commands.Cog):
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
        target: discord.Member, 
        moderator: discord.Member
    ) -> discord.Embed:
        """Returns a standardised success embed."""
        embed = discord.Embed(
            title=title,
            description=description,
            color=discord.Color.from_rgb(60, 180, 100),
            timestamp=discord.utils.utcnow(),
        )
        embed.set_thumbnail(url=target.display_avatar.url)
        embed.set_footer(text=f"Action performed by {moderator} ({moderator.id})")
        return embed

    async def _preflight_role(
        self,
        interaction: discord.Interaction,
        role: discord.Role,
    ) -> bool:
        """
        Run role hierarchy and managed-state checks.
        Sends an ephemeral error and returns False if any check fails.
        """
        if role.managed:
            await interaction.response.send_message(
                embed=self._error_embed(
                    "This is an integration or premium role and cannot be manually assigned or removed."
                ),
                ephemeral=True,
            )
            return False

        if role.is_default():
            await interaction.response.send_message(
                embed=self._error_embed("The default `@everyone` role cannot be modified."),
                ephemeral=True,
            )
            return False

        is_owner = interaction.user.id == interaction.guild.owner_id

        if not is_owner and interaction.user.top_role <= role:
            await interaction.response.send_message(
                embed=self._error_embed(
                    "You cannot manage this role. It is equal to or higher than your highest role."
                ),
                ephemeral=True,
            )
            return False

        if interaction.guild.me.top_role <= role:
            await interaction.response.send_message(
                embed=self._error_embed(
                    "I cannot manage this role. My highest role must be above the target role."
                ),
                ephemeral=True,
            )
            return False

        return True

    role_group = app_commands.Group(
        name="role",
        description="Role management commands.",
        default_permissions=discord.Permissions(manage_roles=True)
    )

    @role_group.command(name="add", description="Assign a role to a member.")
    @app_commands.describe(
        target="The member to receive the role.",
        role="The role to assign."
    )
    async def add_role(
        self, 
        interaction: discord.Interaction, 
        target: discord.Member, 
        role: discord.Role
    ) -> None:
        if not await self._preflight_role(interaction, role):
            return

        if role in target.roles:
            await interaction.response.send_message(
                embed=self._error_embed(f"**{target}** already has the {role.mention} role."),
                ephemeral=True,
            )
            return

        audit_reason = f"Role assigned by {interaction.user} ({interaction.user.id})"

        try:
            await target.add_roles(role, reason=audit_reason)
        except discord.Forbidden:
            await interaction.response.send_message(
                embed=self._error_embed("I lack the required permissions to assign this role."),
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
                title="Role Assigned",
                description=f"Successfully added {role.mention} to **{target}** (`{target.id}`).",
                target=target,
                moderator=interaction.user
            )
        )

    @role_group.command(name="remove", description="Remove a role from a member.")
    @app_commands.describe(
        target="The member to remove the role from.",
        role="The role to remove."
    )
    async def remove_role(
        self, 
        interaction: discord.Interaction, 
        target: discord.Member, 
        role: discord.Role
    ) -> None:
        if not await self._preflight_role(interaction, role):
            return

        if role not in target.roles:
            await interaction.response.send_message(
                embed=self._error_embed(f"**{target}** does not currently have the {role.mention} role."),
                ephemeral=True,
            )
            return

        audit_reason = f"Role removed by {interaction.user} ({interaction.user.id})"

        try:
            await target.remove_roles(role, reason=audit_reason)
        except discord.Forbidden:
            await interaction.response.send_message(
                embed=self._error_embed("I lack the required permissions to remove this role."),
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
                title="Role Removed",
                description=f"Successfully removed {role.mention} from **{target}** (`{target.id}`).",
                target=target,
                moderator=interaction.user
            )
        )

async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(RoleManagement(bot))