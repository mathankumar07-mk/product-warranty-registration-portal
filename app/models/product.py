from datetime import datetime

from sqlalchemy import Column, Date, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from app.core.database import Base


class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    product_name = Column(String(120), nullable=False)
    brand = Column(String(80), nullable=False)
    model_number = Column(String(80), nullable=True)
    serial_number = Column(String(120), nullable=True)
    purchase_date = Column(Date, nullable=False)
    invoice_number = Column(String(80), nullable=False)
    warranty_period_months = Column(Integer, nullable=False, default=12)
    warranty_expiry_date = Column(Date, nullable=False)
    status = Column(String(20), default="active", nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    user = relationship("User", back_populates="products")
    claims = relationship("WarrantyClaim", back_populates="product")
