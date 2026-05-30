# Discord Bot Starter Template

This folder contains a minimal, production-ready template for a Discord bot using **Slash-Only** commands. It is designed to be modular by using Cogs.

## Folder Structure
- `main.py`: The core engine that loads extensions and manages the bot lifecycle.
- `cogs/`: A directory for individual feature modules.

## Features
- **Slash-Only Commands:** Supports modern Discord interaction standards.
- **Auto-Cog-Loader:** Automatically detects and loads every `.py` file found in the `cogs/` folder.
- **Global Sync:** Automatically synchronizes slash commands with Discord upon startup.

## Quick Setup
1. **Requirements:**
   ```bash
   pip install discord.py
2. **Configuration:**
Open `main.py` and set your `TOKEN` in the designated line.
3. **Execution:**
`python main.py`
