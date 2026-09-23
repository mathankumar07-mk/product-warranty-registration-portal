from calendar import monthrange
from datetime import date

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models import Product, WarrantyClaim
from app.schemas.claim import WarrantyClaimCreate
from app.schemas.product import ProductCreate


class ProductService:
    @staticmethod
    def _add_months(value: date, months: int) -> date:
        total_months = value.year * 12 + (value.month - 1) + months
        year, month = divmod(total_months, 12)
        month += 1
        day = min(value.day, monthrange(year, month)[1])
        return date(year, month, day)

    @staticmethod
    def create_product(db: Session, user_id: int, data: ProductCreate) -> Product:
        expiry = data.warranty_expiry_date or ProductService._add_months(
            data.purchase_date, data.warranty_period_months
        )

        product = Product(
            user_id=user_id,
            product_name=data.product_name.strip(),
            brand=data.brand.strip(),
            model_number=data.model_number.strip() if data.model_number else None,
            serial_number=data.serial_number.strip() if data.serial_number else None,
            purchase_date=data.purchase_date,
            invoice_number=data.invoice_number.strip(),
            warranty_period_months=data.warranty_period_months,
            warranty_expiry_date=expiry,
            status="active",
        )
        db.add(product)
        db.commit()
        db.refresh(product)
        return product

    @staticmethod
    def list_user_products(db: Session, user_id: int):
        return (
            db.query(Product)
            .filter(Product.user_id == user_id)
            .order_by(Product.created_at.desc())
            .all()
        )

    @staticmethod
    def get_user_product(db: Session, user_id: int, product_id: int) -> Product:
        product = db.query(Product).filter(Product.id == product_id).first()
        if not product or product.user_id != user_id:
            raise HTTPException(status_code=404, detail="Product not found")
        return product

    @staticmethod
    def get_user_claim(db: Session, user_id: int, claim_id: int) -> WarrantyClaim:
        claim = db.query(WarrantyClaim).filter(WarrantyClaim.id == claim_id).first()
        if not claim or claim.user_id != user_id:
            raise HTTPException(status_code=404, detail="Claim not found")
        return claim

    @staticmethod
    def create_claim(db: Session, user_id: int, data: WarrantyClaimCreate) -> WarrantyClaim:
        product = ProductService.get_user_product(db, user_id, data.product_id)
        claim = WarrantyClaim(
            product_id=product.id,
            user_id=user_id,
            claim_type=data.claim_type.strip(),
            description=data.description.strip(),
            status="pending",
        )
        db.add(claim)
        db.commit()
        db.refresh(claim)
        return claim

    @staticmethod
    def list_user_claims(db: Session, user_id: int):
        return (
            db.query(WarrantyClaim)
            .filter(WarrantyClaim.user_id == user_id)
            .order_by(WarrantyClaim.created_at.desc())
            .all()
        )
