from datetime import date
from decimal import Decimal
from typing import Optional, List
from pydantic import BaseModel, EmailStr, Field, ConfigDict, field_validator

class RegisterIn(BaseModel):
    full_name: str = Field(min_length=2, max_length=160)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
class LoginIn(BaseModel):
    email: EmailStr
    password: str
class UserOut(BaseModel):
    id: int; full_name: str; email: str; role: str
    model_config = ConfigDict(from_attributes=True)
class TokenOut(BaseModel):
    access_token: str; token_type: str = "bearer"; user: UserOut
class CustomerIn(BaseModel):
    @field_validator("email", mode="before")
    @classmethod
    def blank_email_to_none(cls, value):
        return None if value == "" else value
    name: str = Field(min_length=1, max_length=160)
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    company: Optional[str] = None
    address: Optional[str] = None
    tax_id: Optional[str] = None
class ProductIn(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    description: Optional[str] = None
    unit: str = "unit"
    price: Decimal = Field(ge=0, max_digits=12, decimal_places=2)
    tax_rate: Decimal = Field(default=Decimal("0"), ge=0, le=100, max_digits=5, decimal_places=2)
class ItemIn(BaseModel):
    product_id: int
    quantity: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
class InvoiceIn(BaseModel):
    customer_id: int
    issue_date: date
    due_date: Optional[date] = None
    notes: Optional[str] = None
    items: List[ItemIn] = Field(min_length=1, max_length=100)
class PaymentIn(BaseModel):
    amount: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    payment_date: date
    method: str = "bank transfer"
    reference: Optional[str] = None
    notes: Optional[str] = None
class QuoteIn(BaseModel):
    customer_id: int
    issue_date: date
    expiry_date: Optional[date] = None
    total: Decimal = Field(ge=0, max_digits=12, decimal_places=2)
    notes: Optional[str] = None
class ExpenseIn(BaseModel):
    title: str
    category: str = "General"
    amount: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    expense_date: date
    notes: Optional[str] = None
class SettingsIn(BaseModel):
    @field_validator("email", mode="before")
    @classmethod
    def blank_email_to_none(cls, value):
        return None if value == "" else value
    business_name: str = "My Business"
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    currency: str = "INR"
    tax_number: Optional[str] = None
