from sqlalchemy import Column, Integer, String, Boolean, Date, DateTime, ForeignKey, Numeric, Text, func
from sqlalchemy.orm import relationship
from .database import Base

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(160), nullable=False)
    role = Column(String(30), nullable=False, default="admin")
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class Customer(Base):
    __tablename__ = "customers"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(160), nullable=False, index=True)
    email = Column(String(255), nullable=True)
    phone = Column(String(60), nullable=True)
    company = Column(String(160), nullable=True)
    address = Column(Text, nullable=True)
    tax_id = Column(String(100), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    invoices = relationship("Invoice", back_populates="customer")

class Product(Base):
    __tablename__ = "products"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(160), nullable=False, index=True)
    description = Column(Text, nullable=True)
    unit = Column(String(40), default="unit")
    price = Column(Numeric(12,2), nullable=False, default=0)
    tax_rate = Column(Numeric(5,2), nullable=False, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class Invoice(Base):
    __tablename__ = "invoices"
    id = Column(Integer, primary_key=True, index=True)
    invoice_number = Column(String(50), unique=True, nullable=False, index=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)
    issue_date = Column(Date, nullable=False)
    due_date = Column(Date, nullable=True)
    status = Column(String(30), default="draft", nullable=False)
    subtotal = Column(Numeric(12,2), default=0, nullable=False)
    tax_total = Column(Numeric(12,2), default=0, nullable=False)
    total = Column(Numeric(12,2), default=0, nullable=False)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    customer = relationship("Customer", back_populates="invoices")
    items = relationship("InvoiceItem", back_populates="invoice", cascade="all, delete-orphan")
    payments = relationship("Payment", back_populates="invoice", cascade="all, delete-orphan")

class InvoiceItem(Base):
    __tablename__ = "invoice_items"
    id = Column(Integer, primary_key=True, index=True)
    invoice_id = Column(Integer, ForeignKey("invoices.id", ondelete="CASCADE"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=True)
    description = Column(String(255), nullable=False)
    quantity = Column(Numeric(12,2), nullable=False)
    unit_price = Column(Numeric(12,2), nullable=False)
    tax_rate = Column(Numeric(5,2), nullable=False, default=0)
    line_subtotal = Column(Numeric(12,2), nullable=False)
    line_tax = Column(Numeric(12,2), nullable=False)
    line_total = Column(Numeric(12,2), nullable=False)
    invoice = relationship("Invoice", back_populates="items")

class Payment(Base):
    __tablename__ = "payments"
    id = Column(Integer, primary_key=True, index=True)
    invoice_id = Column(Integer, ForeignKey("invoices.id"), nullable=False)
    amount = Column(Numeric(12,2), nullable=False)
    payment_date = Column(Date, nullable=False)
    method = Column(String(50), default="bank transfer")
    reference = Column(String(160), nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    invoice = relationship("Invoice", back_populates="payments")

class Quote(Base):
    __tablename__ = "quotes"
    id = Column(Integer, primary_key=True, index=True)
    quote_number = Column(String(50), unique=True, nullable=False)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)
    issue_date = Column(Date, nullable=False)
    expiry_date = Column(Date, nullable=True)
    status = Column(String(30), default="draft", nullable=False)
    total = Column(Numeric(12,2), default=0, nullable=False)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class Expense(Base):
    __tablename__ = "expenses"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(160), nullable=False)
    category = Column(String(100), default="General")
    amount = Column(Numeric(12,2), nullable=False)
    expense_date = Column(Date, nullable=False)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class BusinessSetting(Base):
    __tablename__ = "business_settings"
    id = Column(Integer, primary_key=True, index=True)
    business_name = Column(String(160), default="My Business", nullable=False)
    email = Column(String(255), nullable=True)
    phone = Column(String(60), nullable=True)
    address = Column(Text, nullable=True)
    currency = Column(String(8), default="INR", nullable=False)
    tax_number = Column(String(100), nullable=True)
