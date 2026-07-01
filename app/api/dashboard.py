from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.models.user import User
from app.models.guild import Guild
from app.models.settings import GuildSettings
from app.models.autorole import AutoRoleRule
from app.models.log import AuditLog
from app.api.deps import get_optional_current_user, get_current_user
from app.core.settings import settings
from app.services.discord import get_discord_guild_roles, get_discord_guild_channels

router = APIRouter()
templates = Jinja2Templates(directory="app/dashboard/templates")

@router.get("/", response_class=HTMLResponse)
async def home(request: Request, user: User | None = Depends(get_optional_current_user)):
    if user:
        return RedirectResponse(url="/dashboard")
    return templates.TemplateResponse(request, "index.html")

@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard_overview(request: Request, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    # Fetch guilds the user owns or manages (for now just all guilds the bot is in, to simplify)
    result = await db.execute(select(Guild).filter_by(is_active=True))
    guilds = result.scalars().all()
    
    return templates.TemplateResponse(request, "dashboard.html", {
        "user": user,
        "guilds": guilds,
        "total_guilds": len(guilds),
        "client_id": settings.DISCORD_CLIENT_ID
    })

@router.get("/dashboard/servers/{guild_id}", response_class=HTMLResponse)
async def server_settings(request: Request, guild_id: int, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Guild).filter_by(id=guild_id))
    guild = result.scalars().first()
    
    if not guild:
        raise HTTPException(status_code=404, detail="Server not found")
        
    # Fetch Settings
    settings_result = await db.execute(select(GuildSettings).filter_by(guild_id=guild_id))
    guild_settings = settings_result.scalars().first()
    if not guild_settings:
        guild_settings = GuildSettings(guild_id=guild_id)
        db.add(guild_settings)
        await db.commit()
        await db.refresh(guild_settings)
        
    # Fetch Rules
    rules_result = await db.execute(
        select(AutoRoleRule).filter_by(guild_id=guild_id).order_by(AutoRoleRule.priority.desc())
    )
    rules = rules_result.scalars().all()
    
    # Fetch live roles and channels from Discord
    roles = await get_discord_guild_roles(guild_id)
    channels = await get_discord_guild_channels(guild_id)
    
    # Filter roles (exclude @everyone and managed bot roles)
    filtered_roles = [
        r for r in roles 
        if r.get("name") != "@everyone" and not r.get("managed")
    ]
    
    # Create a roles map for easy lookup in templates
    roles_map = {int(r["id"]): r for r in roles}
    
    return templates.TemplateResponse(request, "server.html", {
        "user": user,
        "guild": guild,
        "settings": guild_settings,
        "rules": rules,
        "roles": filtered_roles,
        "roles_map": roles_map,
        "channels": channels
    })

@router.post("/dashboard/servers/{guild_id}/settings")
async def save_general_settings(
    request: Request,
    guild_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    form = await request.form()
    autorole_enabled = form.get("autorole_enabled") == "true"
    log_channel_id = form.get("log_channel_id")
    log_channel_id = int(log_channel_id) if log_channel_id else None
    
    result = await db.execute(select(GuildSettings).filter_by(guild_id=guild_id))
    guild_settings = result.scalars().first()
    if not guild_settings:
        guild_settings = GuildSettings(guild_id=guild_id)
        db.add(guild_settings)
        
    guild_settings.autorole_enabled = autorole_enabled
    guild_settings.log_channel_id = log_channel_id
    
    # Write Audit Log
    db.add(AuditLog(
        guild_id=guild_id,
        user_id=user.id,
        action="SETTINGS_UPDATED",
        details={"autorole_enabled": autorole_enabled, "log_channel_id": log_channel_id}
    ))
    
    await db.commit()
    
    return RedirectResponse(url=f"/dashboard/servers/{guild_id}", status_code=303)

@router.post("/dashboard/servers/{guild_id}/rules")
async def add_autorole_rule(
    request: Request,
    guild_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    form = await request.form()
    rule_name = form.get("name", "New Rule")
    target_type = form.get("target_type", "all") # "all", "human", "bot", "user"
    role_ids = form.getlist("role_ids")
    
    if not role_ids:
        raise HTTPException(status_code=400, detail="At least one role is required")
        
    role_ids = [int(rid) for rid in role_ids]
    
    conditions = {"type": target_type}
    if target_type == "user":
        user_id_str = form.get("user_id")
        if not user_id_str:
            raise HTTPException(status_code=400, detail="User ID is required for Specific User target type")
        try:
            conditions["user_id"] = int(user_id_str)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid User ID. Must be a number.")
            
    rule = AutoRoleRule(
        guild_id=guild_id,
        name=rule_name,
        is_enabled=True,
        conditions=conditions,
        roles_to_assign=role_ids
    )
    db.add(rule)
    await db.flush() # Flush to get rule.id before committing
    
    # Write Audit Log
    db.add(AuditLog(
        guild_id=guild_id,
        user_id=user.id,
        action="RULE_CREATED",
        target_id=str(rule.id),
        details={"name": rule_name, "target_type": target_type, "role_ids": role_ids}
    ))
    
    await db.commit()
    
    return RedirectResponse(url=f"/dashboard/servers/{guild_id}", status_code=303)

@router.post("/dashboard/servers/{guild_id}/rules/{rule_id}/delete")
async def delete_autorole_rule(
    guild_id: int,
    rule_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(AutoRoleRule).filter_by(id=rule_id, guild_id=guild_id))
    rule = result.scalars().first()
    if rule:
        # Write Audit Log
        db.add(AuditLog(
            guild_id=guild_id,
            user_id=user.id,
            action="RULE_DELETED",
            target_id=str(rule_id),
            details={"name": rule.name}
        ))
        await db.delete(rule)
        await db.commit()
        
    return RedirectResponse(url=f"/dashboard/servers/{guild_id}", status_code=303)
