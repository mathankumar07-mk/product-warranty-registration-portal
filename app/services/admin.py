"""Admin business logic. All queries run against PostgreSQL via SQLAlchemy."""

from datetime import date

from fastapi import HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models import Product, User, WarrantyClaim

VALID_CLAIM_STATUSES = ("pending", "approved", "rejected")
# Only pending claims may transition to a final state.
ALLOWED_CLAIM_TRANSITIONS = {
    "pending": ("approved", "rejected"),
}


class AdminService:
    @staticmethod
    def get_stats(db: Session) -> dict:
        total_customers = (
            db.query(func.count(User.id)).filter(User.role == "customer").scalar() or 0
        )
        total_admins = (
            db.query(func.count(User.id)).filter(User.role == "admin").scalar() or 0
        )
        total_products = db.query(func.count(Product.id)).scalar() or 0
        total_claims = db.query(func.count(WarrantyClaim.id)).scalar() or 0
        pending_claims = (
            db.query(func.count(WarrantyClaim.id))
            .filter(WarrantyClaim.status == "pending")
            .scalar()
            or 0
        )
        recent_products = (
            db.query(Product).order_by(Product.created_at.desc()).limit(5).all()
        )
        recent_claims = (
            db.query(WarrantyClaim)
            .order_by(WarrantyClaim.created_at.desc())
            .limit(10)
            .all()
        )
        pending_claim_list = (
            db.query(WarrantyClaim)
            .filter(WarrantyClaim.status == "pending")
            .order_by(WarrantyClaim.created_at.desc())
            .limit(10)
            .all()
        )
        return {
            "total_customers": total_customers,
            "total_admins": total_admins,
            "total_products": total_products,
            "total_registrations": total_products,
            "total_claims": total_claims,
            "pending_claims": pending_claims,
            "recent_products": recent_products,
            "recent_claims": recent_claims,
            "pending_claim_list": pending_claim_list,
        }

    @staticmethod
    def list_customers(db: Session, page: int, page_size: int):
        page = max(1, page)
        page_size = min(max(1, page_size), 100)
        query = db.query(User).order_by(User.created_at.desc())
        total = query.count()
        items = query.offset((page - 1) * page_size).limit(page_size).all()
        return {"total": total, "page": page, "page_size": page_size, "items": items}

    @staticmethod
    def get_customer(db: Session, user_id: int) -> User:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="Customer not found")
        return user

    @staticmethod
    def list_products(
        db: Session,
        page: int = 1,
        page_size: int = 50,
        search: str | None = None,
    ):
        page = max(1, page)
        page_size = min(max(1, page_size), 100)
        query = db.query(Product).order_by(Product.created_at.desc())
        if search:
            like = f"%{search.strip()}%"
            query = query.filter(
                (Product.product_name.ilike(like))
                | (Product.brand.ilike(like))
                | (Product.serial_number.ilike(like))
                | (Product.invoice_number.ilike(like))
            )
        total = query.count()
        items = query.offset((page - 1) * page_size).limit(page_size).all()
        return {"total": total, "page": page, "page_size": page_size, "items": items}

    @staticmethod
    def update_product(
        db: Session,
        product_id: int,
        *,
        product_name: str,
        brand: str,
        model_number: str | None,
        serial_number: str | None,
        purchase_date: date,
        invoice_number: str,
        warranty_period_months: int,
        status: str,
    ) -> Product:
        product = db.query(Product).filter(Product.id == product_id).first()
        if not product:
            raise HTTPException(status_code=404, detail="Product not found")
        if status not in ("active", "expired", "claimed"):
            raise HTTPException(status_code=400, detail="Invalid product status.")
        product.product_name = product_name.strip()
        product.brand = brand.strip()
        product.model_number = model_number.strip() if model_number else None
        product.serial_number = serial_number.strip() if serial_number else None
        product.purchase_date = purchase_date
        product.invoice_number = invoice_number.strip()
        product.warranty_period_months = warranty_period_months
        product.status = status
        db.commit()
        db.refresh(product)
        return product

    @staticmethod
    def delete_product(db: Session, product_id: int) -> None:
        product = db.query(Product).filter(Product.id == product_id).first()
        if not product:
            raise HTTPException(status_code=404, detail="Product not found")
        # Delete dependent claims first to avoid FK violations.
        db.query(WarrantyClaim).filter(
            WarrantyClaim.product_id == product_id
        ).delete()
        db.delete(product)
        db.commit()

    @staticmethod
    def list_claims(
        db: Session,
        page: int = 1,
        page_size: int = 50,
        status: str | None = None,
    ):
        page = max(1, page)
        page_size = min(max(1, page_size), 100)
        query = db.query(WarrantyClaim).order_by(WarrantyClaim.created_at.desc())
        if status:
            if status not in VALID_CLAIM_STATUSES:
                raise HTTPException(status_code=400, detail="Invalid claim status.")
            query = query.filter(WarrantyClaim.status == status)
        total = query.count()
        items = query.offset((page - 1) * page_size).limit(page_size).all()
        return {"total": total, "page": page, "page_size": page_size, "items": items}

    @staticmethod
    def get_claim(db: Session, claim_id: int) -> WarrantyClaim:
        claim = db.query(WarrantyClaim).filter(WarrantyClaim.id == claim_id).first()
        if not claim:
            raise HTTPException(status_code=404, detail="Claim not found")
        return claim

    @staticmethod
    def set_claim_status(db: Session, claim_id: int, new_status: str) -> WarrantyClaim:
        if new_status not in VALID_CLAIM_STATUSES:
            raise HTTPException(status_code=400, detail="Invalid claim status.")
        claim = AdminService.get_claim(db, claim_id)
        allowed = ALLOWED_CLAIM_TRANSITIONS.get(claim.status, ())
        if new_status not in allowed:
            raise HTTPException(
                status_code=400,
                detail=f"Cannot change claim from {claim.status} to {new_status}.",
            )
        claim.status = new_status
        db.commit()
        db.refresh(claim)
        return claim
