import discord
from discord import app_commands
from discord.ext import commands
import structlog
from sqlalchemy import select

from app.models.guild import Guild
from app.models.settings import GuildSettings

logger = structlog.get_logger()

class CommandsCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="ping", description="Check bot latency")
    async def ping(self, interaction: discord.Interaction):
        latency = round(self.bot.latency * 1000)
        await interaction.response.send_message(f"Pong! Latency is {latency}ms.", ephemeral=True)

    @app_commands.command(name="dashboard", description="Get a link to the dashboard")
    async def dashboard(self, interaction: discord.Interaction):
        dashboard_url = "https://bot-production-bfc30.up.railway.app"
        
        embed = discord.Embed(
            title="Discord Role Manager Pro Dashboard",
            description=f"Manage your server's AutoRole rules and settings from our web dashboard:\n\n[**Open Dashboard**]({dashboard_url})",
            color=discord.Color.blurple()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="settings", description="View basic server settings")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def settings(self, interaction: discord.Interaction):
        async with self.bot.session_maker() as session:
            result = await session.execute(
                select(GuildSettings).filter_by(guild_id=interaction.guild_id)
            )
            settings = result.scalars().first()
            
            if not settings:
                await interaction.response.send_message("Settings not found for this server. Try kicking and re-inviting the bot.", ephemeral=True)
                return
                
            embed = discord.Embed(title="Server Settings", color=discord.Color.green())
            embed.add_field(name="AutoRole Enabled", value="Yes" if settings.autorole_enabled else "No")
            embed.add_field(name="Log Channel", value=f"<#{settings.log_channel_id}>" if settings.log_channel_id else "Not Set")
            
            await interaction.response.send_message(embed=embed, ephemeral=True)

async def setup(bot):
    await bot.add_cog(CommandsCog(bot))
