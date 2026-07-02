from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import RedirectResponse, HTMLResponse
import httpx
from datetime import datetime, timedelta
from jose import jwt
import urllib.parse
import traceback
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.settings import settings
from app.core.database import get_db
from app.models.user import User

router = APIRouter()

def create_access_token(data: dict, expires_delta: timedelta | None = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt

@router.get("/login")
async def login():
    discord_auth_url = "https://discord.com/api/oauth2/authorize"
    params = {
        "client_id": settings.DISCORD_CLIENT_ID,
        "redirect_uri": settings.DISCORD_REDIRECT_URI,
        "response_type": "code",
        "scope": "identify guilds"
    }
    url = f"{discord_auth_url}?{urllib.parse.urlencode(params)}"
    return RedirectResponse(url)

@router.get("/callback")
async def callback(request: Request, db: AsyncSession = Depends(get_db)):
    # Discord may send an error (e.g. access_denied, redirect_uri_mismatch)
    error = request.query_params.get("error")
    if error:
        error_desc = request.query_params.get("error_description", error)
        return HTMLResponse(
            f"<h2>Discord OAuth Error</h2><p>{error_desc}</p>"
            f"<p>Make sure <code>{settings.DISCORD_REDIRECT_URI}</code> is added "
            f"in Discord Developer Portal → OAuth2 → Redirects.</p>"
            f'<a href="/">Go back</a>',
            status_code=400
        )

    code = request.query_params.get("code")
    if not code:
        raise HTTPException(status_code=400, detail="Missing code parameter")

    try:
        # Exchange code for token
        data = {
            "client_id": settings.DISCORD_CLIENT_ID,
            "client_secret": settings.DISCORD_CLIENT_SECRET,
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": settings.DISCORD_REDIRECT_URI
        }
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        
        async with httpx.AsyncClient() as client:
            token_res = await client.post(
                "https://discord.com/api/oauth2/token", data=data, headers=headers
            )
            if token_res.status_code != 200:
                raise HTTPException(
                    status_code=400,
                    detail=f"Discord token exchange failed: {token_res.text}"
                )
                
            token_data = token_res.json()
            access_token = token_data.get("access_token")
            
            # Get user info
            user_res = await client.get(
                "https://discord.com/api/users/@me",
                headers={"Authorization": f"Bearer {access_token}"}
            )
            if user_res.status_code != 200:
                raise HTTPException(status_code=400, detail="Failed to fetch user info from Discord")
                
            user_data = user_res.json()
            
        user_id = int(user_data["id"])
        
        # Save or update user in database
        result = await db.execute(select(User).filter_by(id=user_id))
        user = result.scalars().first()
        
        if not user:
            user = User(
                id=user_id,
                username=user_data["username"],
                avatar=user_data.get("avatar")
            )
            db.add(user)
        else:
            user.username = user_data["username"]
            user.avatar = user_data.get("avatar")
            
        await db.commit()
        
        # Create JWT
        jwt_token = create_access_token(
            data={"sub": str(user_id)},
            expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        )
        
        # Redirect to dashboard frontend, set cookie
        response = RedirectResponse(url="/dashboard")
        response.set_cookie(key="access_token", value=f"Bearer {jwt_token}", httponly=True)
        return response

    except HTTPException:
        raise
    except Exception as e:
        tb = traceback.format_exc()
        # Return readable error page instead of crashing with 502
        return HTMLResponse(
            f"<h2>Login Error</h2><pre>{tb}</pre>",
            status_code=500
        )

@router.post("/logout")
async def logout(response: Response):
    response.delete_cookie("access_token")
    return {"message": "Logged out successfully"}
