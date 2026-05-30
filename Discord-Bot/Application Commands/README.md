# Application Commands (Slash Commands) Explained

This section breaks down how Discord Application Commands work and how to implement them effectively using `discord.py`. We translate the official API documentation into practical, ready-to-use examples.

## Navigation
* [What are Application Commands?](#what-are-application-commands)
* [Structure of a Command](#structure-of-a-command)
* [Code Examples (Implementation)](#code-examples)

---

## <a name="what-are-application-commands"></a> What are Application Commands?
Application Commands are the native way users interact with apps on Discord (what users know as `/commands`). Instead of parsing message text (like `!ping`), Discord handles the input natively, providing a much cleaner UI and better security.

There are three main types:
1.  **CHAT_INPUT:** The classic Slash Command (e.g., `/ping`).
2.  **USER:** Commands that appear when you right-click a user (User Context Menu).
3.  **MESSAGE:** Commands that appear when you right-click a message (Message Context Menu).

---

## <a name="structure-of-a-command"></a> Structure of a Command (API Breakdown)
When you register a command with Discord, you send a JSON payload. Here is what the key fields from the official documentation actually mean for you as a developer:

| Field | Type | Developer Explanation |
| :--- | :--- | :--- |
| `name` | string | The actual word the user types (e.g., "ban"). Must be lowercase and 1-32 characters. |
| `description` | string | A short text explaining what the command does (1-100 characters). Required for `CHAT_INPUT`. |
| `options` | array | Arguments the user can pass (e.g., selecting a user to ban, or typing a reason). |
| `default_member_permissions` | string | Defines who can use this by default (e.g., only users with "Ban Members" permission). |

---

## <a name="code-examples"></a> Code Examples (Implementation)
Here is how you translate the API structure into functional `discord.py` code using Cogs.

### 1. The Basic Command (`CHAT_INPUT`)
```python
import discord
from discord import app_commands
from discord.ext import commands

class BasicCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # 'name' and 'description' map directly to the API fields.
    @app_commands.command(name="hello", description="Says hello to the user")
    async def hello(self, interaction: discord.Interaction):
        await interaction.response.send_message(f"Hello, {interaction.user.name}!")

async def setup(bot):
    await bot.add_cog(BasicCommands(bot))
