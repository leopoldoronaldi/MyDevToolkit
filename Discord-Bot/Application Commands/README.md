# Application Commands

Application Commands (Slash Commands) require strict adherence to Discord's API specifications. This document outlines standard implementation patterns and highlights common structural constraints to ensure application stability.

---

## Common Implementation Constraints

### 1. Interaction Response Timeout (3-Second Limit)
* **Constraint:** Discord requires an initial response to any application command within exactly 3 seconds. Failure to respond results in an "Interaction Failed" state for the user.
* **Standard Practice:** For commands requiring database queries, external API calls, or complex calculations, utilize `interaction.response.defer()` immediately upon execution to extend the timeout window to 15 minutes.

### 2. Rate Limiting via Excessive Global Syncs
* **Constraint:** Executing `bot.tree.sync()` globally on every application startup will trigger Discord's rate limits. Global synchronizations are highly cached and can take up to an hour to propagate across all clients.
* **Standard Practice:** Restrict global syncing to production deployments. During active development, sync commands exclusively to a designated testing guild (server).

### 3. Invalid Command Naming Conventions
* **Constraint:** Command names and option parameters must strictly follow Discord's naming regex. 
* **Standard Practice:** Use exclusively lowercase alphanumeric characters. Spaces are not permitted; utilize underscores (`_`) or hyphens (`-`) for separation. Maximum length is 32 characters.

---

## Implementation Templates

The following modular examples utilize `discord.app_commands` and are structured to be loaded dynamically via Cogs.

### 1. Baseline Command Structure
The minimal required architecture for a valid application command.

```python
import discord
from discord import app_commands
from discord.ext import commands

class CoreCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(
        name="status",
        description="Returns the current operational status."
    )
    async def status(self, interaction: discord.Interaction):
        # ephemeral=True restricts visibility to the executing user
        await interaction.response.send_message("System operational.", ephemeral=True)

async def setup(bot):
    await bot.add_cog(CoreCommands(bot))
```
### 2. Deferred Response
Implementation for tasks exceeding the standard 3-second timeout threshold.
```python
@app_commands.command(
        name="process_data", 
        description="Executes a long-running background task."
    )
    async def process_data(self, interaction: discord.Interaction):
        # Extend the timeout window
        await interaction.response.defer(ephemeral=False) 
        
        import asyncio
        await asyncio.sleep(5) # Placeholder for complex logic
        
        # Follow-up must be used after deferring
        await interaction.followup.send("Task completed successfully.")
```
### 3. Type-Hinted Command Parameters
Implementation of user input validation via strict type hinting.
```python
@app_commands.command(
        name="moderate_user", 
        description="Applies moderation action to a specific member."
    )
    @app_commands.describe(
        target_member="The member object to moderate.",
        reason="Documentation for the audit log."
    )
    async def moderate_user(
        self, 
        interaction: discord.Interaction, 
        target_member: discord.Member, 
        reason: str
    ):
        await interaction.response.send_message(
            f"Action applied to {target_member.id}. Reason: {reason}"
        )
```
### 4. Predefined Parameter Choices
Enforcing restricted input values using Choice objects.
```python
@app_commands.command(
        name="set_environment", 
        description="Configures the target environment."
    )
    @app_commands.choices(environment=[
        app_commands.Choice(name="Production", value="prod"),
        app_commands.Choice(name="Staging", value="stage"),
        app_commands.Choice(name="Development", value="dev")
    ])
    async def set_environment(
        self, 
        interaction: discord.Interaction, 
        environment: app_commands.Choice[str]
    ):
        await interaction.response.send_message(f"Environment set to: {environment.value}")
```
### 5. Role-Based Access Control
```python
@app_commands.command(
        name="purge_cache", 
        description="Clears the application cache."
    )
    # Command will not render in the UI for unauthorized users
    @app_commands.default_permissions(administrator=True) 
    async def purge_cache(self, interaction: discord.Interaction):
        await interaction.response.send_message("Cache purged.", ephemeral=True)
```
