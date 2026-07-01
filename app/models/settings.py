from sqlalchemy import String, BigInteger, Boolean, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

class GuildSettings(Base):
    __tablename__ = "guild_settings"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    guild_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("guilds.id", ondelete="CASCADE"), unique=True)
    
    # General settings
    autorole_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    log_channel_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    
    guild: Mapped["Guild"] = relationship(back_populates="settings")
