from typing import Optional

import discord
from discord import app_commands
from discord.ext import commands

class UtilityInformation(commands.Cog):
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

    @app_commands.command(
        name="userinfo", 
        description="Display detailed information about a member."
    )
    @app_commands.describe(
        target="The member to inspect. Defaults to yourself."
    )
    async def userinfo(
        self,
        interaction: discord.Interaction,
        target: Optional[discord.Member] = None
    ) -> None:
        member = target or interaction.user

        embed = discord.Embed(
            title="User Information",
            color=discord.Color.from_rgb(100, 140, 210),
            timestamp=discord.utils.utcnow(),
        )
        
        if member.display_avatar:
            embed.set_thumbnail(url=member.display_avatar.url)
        
        created_time = int(member.created_at.timestamp())
        joined_time = int(member.joined_at.timestamp()) if member.joined_at else 0

        roles = [role.mention for role in reversed(member.roles) if role.name != "@everyone"]
        roles_display = " ".join(roles[:15])
        if len(roles) > 15:
            roles_display += f" ... and {len(roles) - 15} more"
        if not roles_display:
            roles_display = "No specific roles"

        embed.add_field(
            name="Account Details", 
            value=f"**User:** {member.mention}\n**ID:** `{member.id}`\n**Bot Profile:** {'Yes' if member.bot else 'No'}", 
            inline=True
        )
        embed.add_field(
            name="Guild Details", 
            value=f"**Nickname:** {member.nick or 'None'}\n**Top Role:** {member.top_role.mention}", 
            inline=True
        )
        
        embed.add_field(
            name="Registration Dates", 
            value=f"**Created:** <t:{created_time}:F> (<t:{created_time}:R>)\n**Joined:** <t:{joined_time}:F> (<t:{joined_time}:R>)", 
            inline=False
        )
        
        embed.add_field(
            name=f"Roles [{len(roles)}]", 
            value=roles_display, 
            inline=False
        )
        
        embed.set_footer(text=f"Requested by {interaction.user} ({interaction.user.id})")

        await interaction.response.send_message(embed=embed)


    @app_commands.command(
        name="serverinfo", 
        description="Display detailed information about the current server."
    )
    async def serverinfo(self, interaction: discord.Interaction) -> None:
        guild = interaction.guild
        if not guild:
            await interaction.response.send_message(
                embed=self._error_embed("This command can only be executed within a server environment."),
                ephemeral=True
            )
            return

        embed = discord.Embed(
            title="Server Information",
            description=f"**{guild.name}** (`{guild.id}`)",
            color=discord.Color.from_rgb(100, 140, 210),
            timestamp=discord.utils.utcnow(),
        )
        
        if guild.icon:
            embed.set_thumbnail(url=guild.icon.url)
        if guild.banner:
            embed.set_image(url=guild.banner.url)
        
        created_time = int(guild.created_at.timestamp())
        owner = guild.owner
        
        bots = sum(1 for member in guild.members if member.bot)
        humans = guild.member_count - bots

        embed.add_field(
            name="General", 
            value=f"**Owner:** {owner.mention if owner else 'Unknown'}\n**Created:** <t:{created_time}:D> (<t:{created_time}:R>)", 
            inline=False
        )
        
        embed.add_field(
            name="Statistics", 
            value=f"**Total Members:** {guild.member_count}\n**Demographics:** {humans} Humans, {bots} Bots\n**Roles:** {len(guild.roles)}\n**Channels:** {len(guild.channels)}", 
            inline=True
        )
        
        embed.add_field(
            name="Features & Level", 
            value=f"**Boost Tier:** Level {guild.premium_tier}\n**Active Boosts:** {guild.premium_subscription_count}\n**Emoji Limit:** {guild.emoji_limit}", 
            inline=True
        )

        embed.set_footer(text=f"Requested by {interaction.user} ({interaction.user.id})")

        await interaction.response.send_message(embed=embed)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(UtilityInformation(bot))