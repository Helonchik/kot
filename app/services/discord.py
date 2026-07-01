import httpx
from typing import List, Dict, Any
from app.core.settings import settings
import structlog

logger = structlog.get_logger()

async def get_discord_guild_roles(guild_id: int) -> List[Dict[str, Any]]:
    url = f"https://discord.com/api/v10/guilds/{guild_id}/roles"
    headers = {"Authorization": f"Bot {settings.DISCORD_BOT_TOKEN}"}
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, headers=headers)
            if response.status_code == 200:
                return response.json()
            else:
                logger.error("discord_api_error", status_code=response.status_code, body=response.text)
                return []
        except Exception as e:
            logger.error("discord_api_exception", error=str(e))
            return []

async def get_discord_guild_channels(guild_id: int) -> List[Dict[str, Any]]:
    url = f"https://discord.com/api/v10/guilds/{guild_id}/channels"
    headers = {"Authorization": f"Bot {settings.DISCORD_BOT_TOKEN}"}
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, headers=headers)
            if response.status_code == 200:
                # Filter for text channels (type 0)
                channels = response.json()
                return [c for c in channels if c.get("type") == 0]
            else:
                logger.error("discord_api_error", status_code=response.status_code, body=response.text)
                return []
        except Exception as e:
            logger.error("discord_api_exception", error=str(e))
            return []
