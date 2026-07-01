from sqlalchemy import String, Boolean, BigInteger
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import List

from app.models.base import Base

class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, index=True) # Discord User ID
    username: Mapped[str] = mapped_column(String, nullable=False)
    avatar: Mapped[str | None] = mapped_column(String, nullable=True)
    is_bot: Mapped[bool] = mapped_column(Boolean, default=False)
    
    # Dashboard roles (e.g. is this user a global admin for our dashboard?)
    is_global_admin: Mapped[bool] = mapped_column(Boolean, default=False)

    # We will add relationships as we define other tables
