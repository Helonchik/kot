import discord
from discord.ext import commands
import structlog
import os

from app.core.settings import settings
from app.core.database import AsyncSessionLocal
from app.models.guild import Guild
from sqlalchemy import select

logger = structlog.get_logger()

class RoleManagerBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.members = True # Required for member join events
        intents.message_content = True
        
        super().__init__(
            command_prefix="rm!", 
            intents=intents,
            help_command=None
        )
        self.session_maker = AsyncSessionLocal

    async def setup_hook(self):
        # Load cogs
        cogs_dir = os.path.join(os.path.dirname(__file__), "cogs")
        for filename in os.listdir(cogs_dir):
            if filename.endswith(".py") and not filename.startswith("_"):
                await self.load_extension(f"app.bot.cogs.{filename[:-3]}")
                logger.info("loaded_cog", cog=filename)
        
        # Sync slash commands
        await self.tree.sync()
        logger.info("slash_commands_synced")

def start_bot():
    bot = RoleManagerBot()
    bot.run(settings.DISCORD_BOT_TOKEN)

if __name__ == "__main__":
    start_bot()
