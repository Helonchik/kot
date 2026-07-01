import discord
from discord.ext import commands
import structlog
from sqlalchemy import select
from datetime import datetime, timezone

from app.models.guild import Guild
from app.models.settings import GuildSettings
from app.models.autorole import AutoRoleRule
from app.models.log import AuditLog

logger = structlog.get_logger()

class EventsCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        logger.info("bot_ready", user=str(self.bot.user), guild_count=len(self.bot.guilds))
        async with self.bot.session_maker() as session:
            # Get list of existing guild IDs in DB
            result = await session.execute(select(Guild))
            db_guilds = {g.id: g for g in result.scalars().all()}
            
            # Sync active guilds
            for guild in self.bot.guilds:
                if guild.id in db_guilds:
                    db_guild = db_guilds[guild.id]
                    db_guild.is_active = True
                    db_guild.name = guild.name
                    db_guild.icon = guild.icon.url if guild.icon else None
                    db_guild.owner_id = guild.owner_id
                    db_guild.member_count = guild.member_count
                else:
                    db_guild = Guild(
                        id=guild.id,
                        name=guild.name,
                        icon=guild.icon.url if guild.icon else None,
                        owner_id=guild.owner_id,
                        member_count=guild.member_count,
                        is_active=True
                    )
                    session.add(db_guild)
                    
                    # Add default settings
                    settings = GuildSettings(guild_id=guild.id)
                    session.add(settings)
            
            # Deactivate guilds the bot left while offline
            active_bot_guild_ids = {g.id for g in self.bot.guilds}
            for g_id, db_guild in db_guilds.items():
                if g_id not in active_bot_guild_ids:
                    db_guild.is_active = False
            
            await session.commit()
            logger.info("guilds_synced_with_database")

    @commands.Cog.listener()
    async def on_guild_join(self, guild: discord.Guild):
        logger.info("guild_joined", guild_id=guild.id, guild_name=guild.name)
        async with self.bot.session_maker() as session:
            # Check if guild exists
            result = await session.execute(select(Guild).filter_by(id=guild.id))
            db_guild = result.scalars().first()
            
            if not db_guild:
                db_guild = Guild(
                    id=guild.id,
                    name=guild.name,
                    icon=guild.icon.url if guild.icon else None,
                    owner_id=guild.owner_id,
                    member_count=guild.member_count,
                    is_active=True
                )
                session.add(db_guild)
                
                # Add default settings
                settings = GuildSettings(guild_id=guild.id)
                session.add(settings)
                
            else:
                db_guild.is_active = True
                db_guild.name = guild.name
                
            await session.commit()

    @commands.Cog.listener()
    async def on_guild_remove(self, guild: discord.Guild):
        logger.info("guild_removed", guild_id=guild.id, guild_name=guild.name)
        async with self.bot.session_maker() as session:
            result = await session.execute(select(Guild).filter_by(id=guild.id))
            db_guild = result.scalars().first()
            if db_guild:
                db_guild.is_active = False
                await session.commit()

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        logger.info("member_joined", member_id=member.id, guild_id=member.guild.id)
        # We will handle AutoRole logic here or via Celery for heavy lifting
        # For now, let's do a synchronous database check
        async with self.bot.session_maker() as session:
            # Check if autorole is enabled
            result = await session.execute(
                select(GuildSettings).filter_by(guild_id=member.guild.id)
            )
            settings = result.scalars().first()
            
            if not settings or not settings.autorole_enabled:
                return
                
            # Fetch rules
            rules_result = await session.execute(
                select(AutoRoleRule)
                .filter_by(guild_id=member.guild.id, is_enabled=True)
                .order_by(AutoRoleRule.priority.desc())
            )
            rules = rules_result.scalars().all()
            
            roles_to_assign = set()
            for rule in rules:
                # Basic condition check (mock implementation, you'd expand this)
                conditions = rule.conditions
                passed = True
                
                if conditions.get("type") == "bot":
                    if not member.bot: passed = False
                elif conditions.get("type") == "human":
                    if member.bot: passed = False
                elif conditions.get("type") == "user":
                    target_user_id = conditions.get("user_id")
                    if not target_user_id or member.id != int(target_user_id):
                        passed = False
                
                if passed:
                    for role_id in rule.roles_to_assign:
                        roles_to_assign.add(role_id)
            
            if roles_to_assign:
                discord_roles = []
                for rid in roles_to_assign:
                    role = member.guild.get_role(rid)
                    if role:
                        discord_roles.append(role)
                
                if discord_roles:
                    try:
                        await member.add_roles(*discord_roles, reason="AutoRole Manager")
                        logger.info("autoroles_assigned", member_id=member.id, roles=[r.id for r in discord_roles])
                        
                        # Add Audit Log
                        session.add(AuditLog(
                            guild_id=member.guild.id,
                            user_id=member.id,
                            action="ROLE_ASSIGNED",
                            target_id=str(member.id),
                            details={"roles": [r.name for r in discord_roles], "role_ids": [r.id for r in discord_roles]}
                        ))
                        await session.commit()
                        
                    except discord.Forbidden:
                        logger.warning("autorole_forbidden", guild_id=member.guild.id)
                    except Exception as e:
                        logger.error("autorole_error", error=str(e), guild_id=member.guild.id)

async def setup(bot):
    await bot.add_cog(EventsCog(bot))
