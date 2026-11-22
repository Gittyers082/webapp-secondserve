"""Users and their role-specific profiles (ERD: User, Seller, Buyer and Partner Profile)."""

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, Timestamps, UUIDPrimaryKey
from app.models.enums import AccountStatus, Decision, Role, str_enum


class User(Timestamps, Base):
    """One row per Supabase Auth user. `id` is the same UUID as auth.users.id."""

    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String(120))
    phone: Mapped[str | None] = mapped_column(String(30))
    role: Mapped[Role] = mapped_column(str_enum(Role), index=True)
    status: Mapped[AccountStatus] = mapped_column(
        str_enum(AccountStatus), default=AccountStatus.active, index=True
    )
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    seller_profile: Mapped["SellerProfile | None"] = relationship(
        back_populates="user", uselist=False, lazy="selectin"
    )
    buyer_profile: Mapped["BuyerProfile | None"] = relationship(
        back_populates="user", uselist=False, lazy="selectin"
    )
    partner_profile: Mapped["PartnerProfile | None"] = relationship(
        back_populates="user", uselist=False, lazy="selectin"
    )


class SellerProfile(Timestamps, Base):
    __tablename__ = "seller_profiles"

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    business_name: Mapped[str] = mapped_column(String(120), index=True)
    business_type: Mapped[str] = mapped_column(String(50))  # bakery, grocery, cafe, ...
    business_address: Mapped[str] = mapped_column(String(255))  # default pickup location
    contact_phone: Mapped[str] = mapped_column(String(30))
    description: Mapped[str | None] = mapped_column(Text)
    logo_url: Mapped[str | None] = mapped_column(String(500))
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    user: Mapped[User] = relationship(back_populates="seller_profile")


class BuyerProfile(Timestamps, Base):
    __tablename__ = "buyer_profiles"

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    # Favourite categories, price range, last searches (NFR-USER-PERS-1/2).
    preferences: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)

    user: Mapped[User] = relationship(back_populates="buyer_profile")


class PartnerProfile(Timestamps, Base):
    """An LGU, government agency, charity or shelter that receives surplus (FR-USER-P-1)."""

    __tablename__ = "partner_profiles"

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    organization_name: Mapped[str] = mapped_column(String(160), index=True)
    # lgu, government-agency, charity, shelter
    organization_type: Mapped[str] = mapped_column(String(40))
    contact_person: Mapped[str] = mapped_column(String(120))
    address: Mapped[str] = mapped_column(String(255))  # default pickup/delivery point
    # Link to proof of accreditation, e.g. DSWD registration or an LGU office ID (FR-USER-P-2).
    accreditation_url: Mapped[str | None] = mapped_column(String(500))
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    user: Mapped[User] = relationship(back_populates="partner_profile")


class AccountDecision(UUIDPrimaryKey, Timestamps, Base):
    """Admin approve/decline record, shown on /admin/decisions."""

    __tablename__ = "account_decisions"

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    admin_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    decision: Mapped[Decision] = mapped_column(str_enum(Decision))
    reason: Mapped[str | None] = mapped_column(Text)
