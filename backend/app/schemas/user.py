from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import Field, model_validator

from app.models import AccountStatus, Decision, Role
from app.schemas.common import Schema


class SellerDetails(Schema):
    business_name: str = Field(min_length=2, max_length=120)
    business_type: str = Field(min_length=2, max_length=50)
    business_address: str = Field(min_length=5, max_length=255)
    contact_phone: str = Field(min_length=7, max_length=30)
    description: str | None = Field(default=None, max_length=2000)


class ProfileCreate(Schema):
    """Sent right after Supabase sign-up to finish registration (UC-01)."""

    role: Literal["buyer", "seller"]  # nobody can sign themselves up as admin
    username: str = Field(min_length=3, max_length=50, pattern=r"^[A-Za-z0-9_.]+$")
    full_name: str = Field(min_length=2, max_length=120)
    phone: str | None = Field(default=None, max_length=30)
    seller: SellerDetails | None = None

    @model_validator(mode="after")
    def seller_needs_business(self) -> "ProfileCreate":
        if self.role == "seller" and self.seller is None:
            raise ValueError("Sellers must include their business details.")
        return self


class ProfileUpdate(Schema):
    full_name: str | None = Field(default=None, min_length=2, max_length=120)
    phone: str | None = Field(default=None, max_length=30)
    seller: SellerDetails | None = None


class SellerProfileOut(Schema):
    business_name: str
    business_type: str
    business_address: str
    contact_phone: str
    description: str | None
    logo_url: str | None
    verified_at: datetime | None


class UserOut(Schema):
    id: UUID
    email: str
    username: str
    full_name: str
    phone: str | None
    role: Role
    status: AccountStatus
    created_at: datetime
    seller_profile: SellerProfileOut | None = None


class DecisionIn(Schema):
    decision: Decision
    reason: str | None = Field(default=None, max_length=500)


class DecisionOut(Schema):
    id: UUID
    user_id: UUID
    username: str
    role: Role
    shop_name: str | None
    decision: Decision
    reason: str | None
    created_at: datetime
