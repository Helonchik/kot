from sqlalchemy import String, BigInteger, Boolean, ForeignKey, Integer, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import Dict, Any

from app.models.base import Base

class AutoRoleRule(Base):
    __tablename__ = "autorole_rules"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    guild_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("guilds.id", ondelete="CASCADE"))
    
    name: Mapped[str] = mapped_column(String, nullable=False)
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    priority: Mapped[int] = mapped_column(Integer, default=0) # Higher means evaluated first
    
    # JSON field defining conditions: {"type": "account_age", "operator": ">=", "value": 30}
    # Or complex AND/OR logic
    conditions: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict)
    
    # List of role IDs to assign
    roles_to_assign: Mapped[list[int]] = mapped_column(JSON, default=list)
    
    # Delay in seconds before assigning
    delay_seconds: Mapped[int] = mapped_column(Integer, default=0)

    guild: Mapped["Guild"] = relationship(back_populates="rules")
