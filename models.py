from __future__ import annotations

from datetime import datetime, timezone
from enum import StrEnum

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class GiveawayType(StrEnum):
    AUTO = "auto"
    MANUAL = "manual"


class GiveawayStatus(StrEnum):
    DRAFT = "draft"
    ACTIVE = "active"
    FINISHED = "finished"
    CANCELLED = "cancelled"


class EntrySource(StrEnum):
    COMMENT = "comment"
    BUTTON = "button"


class DeliveryStatus(StrEnum):
    PENDING = "pending"
    SENT = "sent"
    FAILED = "failed"
    MANUAL_REQUIRED = "manual_required"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True, nullable=False)
    username: Mapped[str | None] = mapped_column(String(64), nullable=True)
    first_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    is_registered: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_banned: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    blocked_bot: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    wins_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    entries_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)

    entries: Mapped[list["GiveawayEntry"]] = relationship(back_populates="user")
    wins: Mapped[list["GiveawayWinner"]] = relationship(back_populates="user")


class Giveaway(Base):
    __tablename__ = "giveaways"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    type: Mapped[str] = mapped_column(String(16), index=True, nullable=False)
    status: Mapped[str] = mapped_column(String(16), index=True, nullable=False, default=GiveawayStatus.ACTIVE.value)

    title: Mapped[str] = mapped_column(String(256), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    prize_name: Mapped[str] = mapped_column(String(256), nullable=False)
    gift_id: Mapped[str | None] = mapped_column(String(256), nullable=True)
    winners_count: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    image_file_id: Mapped[str | None] = mapped_column(String(512), nullable=True)

    channel_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    channel_message_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    discussion_chat_id: Mapped[str | None] = mapped_column(String(64), index=True, nullable=True)
    discussion_root_message_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    discussion_message_thread_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    announcement_message_id: Mapped[int | None] = mapped_column(Integer, nullable=True)

    min_participants: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    require_subscription: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_by: Mapped[int | None] = mapped_column(BigInteger, nullable=True)

    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    ends_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    entries: Mapped[list["GiveawayEntry"]] = relationship(back_populates="giveaway", cascade="all, delete-orphan")
    winners: Mapped[list["GiveawayWinner"]] = relationship(back_populates="giveaway", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_giveaway_discussion_root", "discussion_chat_id", "discussion_root_message_id"),
        Index("ix_giveaway_thread", "discussion_chat_id", "discussion_message_thread_id"),
    )


class GiveawayEntry(Base):
    __tablename__ = "giveaway_entries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    giveaway_id: Mapped[int] = mapped_column(ForeignKey("giveaways.id", ondelete="CASCADE"), nullable=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    telegram_id: Mapped[int] = mapped_column(BigInteger, index=True, nullable=False)
    comment_message_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    source: Mapped[str] = mapped_column(String(16), nullable=False)
    is_valid: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    giveaway: Mapped[Giveaway] = relationship(back_populates="entries")
    user: Mapped[User] = relationship(back_populates="entries")

    __table_args__ = (
        UniqueConstraint("giveaway_id", "user_id", name="uq_entry_giveaway_user"),
    )


class GiveawayWinner(Base):
    __tablename__ = "giveaway_winners"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    giveaway_id: Mapped[int] = mapped_column(ForeignKey("giveaways.id", ondelete="CASCADE"), nullable=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    gift_id: Mapped[str | None] = mapped_column(String(256), nullable=True)
    delivery_status: Mapped[str] = mapped_column(String(32), default=DeliveryStatus.PENDING.value, nullable=False)
    delivery_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    selected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    giveaway: Mapped[Giveaway] = relationship(back_populates="winners")
    user: Mapped[User] = relationship(back_populates="wins")

    __table_args__ = (
        UniqueConstraint("giveaway_id", "user_id", name="uq_winner_giveaway_user"),
    )


class AdminLog(Base):
    __tablename__ = "admin_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    admin_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    action: Mapped[str] = mapped_column(String(128), nullable=False)
    payload: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
