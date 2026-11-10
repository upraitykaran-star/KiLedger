from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


class InputModel(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")


class RegisterIn(InputModel):
    name: str = Field(min_length=1, max_length=80)
    business_name: str = Field(min_length=1, max_length=100)
    email: EmailStr
    password: str = Field(min_length=12, max_length=128)

    @field_validator("password")
    @classmethod
    def password_not_common(cls, value: str) -> str:
        if value.lower() in {"password123!", "qwerty123456", "123456789012"}:
            raise ValueError("Choose a less common password")
        return value


class LoginIn(InputModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class BusinessIn(InputModel):
    name: str = Field(min_length=1, max_length=100)


class CustomerIn(InputModel):
    name: str = Field(min_length=1, max_length=80)
    email: EmailStr | None = None
    phone: str | None = Field(default=None, max_length=30)
    notes: str = Field(default="", max_length=1000)


class TransactionIn(InputModel):
    description: str = Field(min_length=1, max_length=100)
    amount_minor: int = Field(gt=0, le=100_000_000_000)
    currency: Literal["INR"] = "INR"
    type: Literal["income", "expense", "payment"]
    customer_id: str | None = None
    date: date
    method: Literal["UPI", "Cash", "Bank transfer", "Card", "Other"] = "Other"
    on_credit: bool = False

    @field_validator("customer_id")
    @classmethod
    def normalize_customer_id(cls, value: str | None) -> str | None:
        if value == "":
            return None
        return value

    @field_validator("on_credit")
    @classmethod
    def credit_only_for_income(cls, value: bool, info):
        if value and info.data.get("type") != "income":
            raise ValueError("Only income can be recorded on credit")
        return value


class RoleIn(InputModel):
    role: Literal["admin", "staff"]


class Page(BaseModel):
    items: list[dict]
    page: int
    page_size: int
    total: int
