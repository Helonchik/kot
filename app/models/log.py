from sqlalchemy import String, BigInteger, JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base
from typing import Dict, Any

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    guild_id: Mapped[int] = mapped_column(BigInteger, index=True, nullable=True)
    user_id: Mapped[int] = mapped_column(BigInteger, index=True, nullable=True)
    
    action: Mapped[str] = mapped_column(String, nullable=False) # e.g. "ROLE_ASSIGNED", "RULE_CREATED"
    target_id: Mapped[str | None] = mapped_column(String, nullable=True) # e.g. role ID or rule ID
    
    details: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict)
