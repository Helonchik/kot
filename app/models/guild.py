from sqlalchemy import String, BigInteger, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import List

from app.models.base import Base

class Guild(Base):
    __tablename__ = "guilds"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, index=True) # Discord Guild ID
    name: Mapped[str] = mapped_column(String, nullable=False)
    icon: Mapped[str | None] = mapped_column(String, nullable=True)
    owner_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    member_count: Mapped[int] = mapped_column(default=0)
    
    # Is the bot currently in this guild?
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    settings: Mapped["GuildSettings"] = relationship(back_populates="guild", uselist=False, cascade="all, delete-orphan")
    rules: Mapped[List["AutoRoleRule"]] = relationship(back_populates="guild", cascade="all, delete-orphan")
