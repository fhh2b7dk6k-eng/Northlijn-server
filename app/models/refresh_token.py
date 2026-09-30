import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db_types import GUID
from app.database import Base


class RefreshToken(Base):
    """Refresh tokens are opaque, random strings on the client side — only
    a SHA-256 hash of the token is ever stored here. This (unlike a
    stateless JWT) is what makes logout/revocation actually work: we can
    mark a specific row revoked, which a JWT alone could never support
    without a separate blocklist.

    `family_id` groups every refresh token descended from one login,
    letting reuse-detection be added later (a revoked token presented
    again is a strong signal of theft, and would let you revoke the whole
    family) without a schema migration.
    """

    __tablename__ = "refresh_tokens"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    token_hash: Mapped[str] = mapped_column(String, unique=True, index=True, nullable=False)
    family_id: Mapped[uuid.UUID] = mapped_column(GUID(), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
