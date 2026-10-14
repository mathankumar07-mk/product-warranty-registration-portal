"""Secure Admin Section.

All routes verify ``User.role == "admin"`` server-side from PostgreSQL.
Role is never trusted from the request body. Customer HTML routes redirect
to /login when unauthenticated; admin HTML routes redirect to /login when
unauthenticated and return 403 for authenticated non-admins. JSON admin APIs
return 401/403 respectively.
"""

from datetime import date

from fastapi import APIRouter, Depends, Form, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.api.deps import get_current_admin, get_logged_in_user
from app.core.csrf import get_csrf_token, validate_csrf_token
from app.core.database import get_db
from app.models import User
from app.schemas.claim import ClaimStatusUpdate, WarrantyClaimRead
from app.schemas.product import AdminProductUpdate, ProductRead
from app.schemas.user import UserRead
from app.services.admin import AdminService
from app.services.product import ProductService

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


def _require_admin_html(request: Request, db: Session) -> User:
    # Manual check (instead of Depends) so routes can redirect
    # unauthenticated browsers to /login while returning 403 for non-admins.
    user = get_logged_in_user(request, db)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    db.refresh(user)
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return user


def _admin_context(request: Request, admin: User, extra: dict | None = None) -> dict:
    ctx: dict = {
        "current_user": admin,
        "user": admin,
        "csrf_token": get_csrf_token(request),
    }
    if extra:
        ctx.update(extra)
    return ctx


# ---------------------------------------------------------------- HTML ----
@router.get("/admin/dashboard", response_class=HTMLResponse)
def admin_dashboard(
    request: Request, db: Session = Depends(get_db)
):
    username = request.session.get("username")
    if not username:
        return RedirectResponse(url="/login", status_code=303)
    admin = _require_admin_html(request, db)
    stats = AdminService.get_stats(db)
    return templates.TemplateResponse(
        request=request,
        name="admin_dashboard.html",
        context=_admin_context(request, admin, {"stats": stats}),
    )


@router.get("/admin/customers", response_class=HTMLResponse)
def admin_customers_page(
    request: Request,
    db: Session = Depends(get_db),
    page: int = Query(default=1, ge=1, le=10000),
    page_size: int = Query(default=20, ge=1, le=100),
):
    if not request.session.get("username"):
        return RedirectResponse(url="/login", status_code=303)
    admin = _require_admin_html(request, db)
    result = AdminService.list_customers(db, page, page_size)
    total_pages = max(1, (result["total"] + page_size - 1) // page_size)
    return templates.TemplateResponse(
        request=request,
        name="admin_customers.html",
        context=_admin_context(
            request,
            admin,
            {
                "customers": result["items"],
                "total": result["total"],
                "page": page,
                "page_size": page_size,
                "total_pages": total_pages,
            },
        ),
    )


@router.get("/admin/products", response_class=HTMLResponse)
def admin_products_page(
    request: Request,
    db: Session = Depends(get_db),
    page: int = Query(default=1, ge=1, le=10000),
    search: str | None = Query(default=None, max_length=120),
):
    if not request.session.get("username"):
        return RedirectResponse(url="/login", status_code=303)
    admin = _require_admin_html(request, db)
    result = AdminService.list_products(db, page, 50, search)
    customers = (
        db.query(User).order_by(User.username.asc()).limit(500).all()
    )
    return templates.TemplateResponse(
        request=request,
        name="admin_products.html",
        context=_admin_context(
            request,
            admin,
            {
                "products": result["items"],
                "total": result["total"],
                "page": page,
                "search": search or "",
                "customers": customers,
                "error": None,
            },
        ),
    )


@router.post("/admin/products", response_class=HTMLResponse)
def admin_create_product(
    request: Request,
    db: Session = Depends(get_db),
    csrf_token: str = Form(...),
    owner_id: int = Form(...),
    product_name: str = Form(..., min_length=2, max_length=120),
    brand: str = Form(..., min_length=2, max_length=80),
    model_number: str = Form(default=""),
    serial_number: str = Form(default=""),
    purchase_date: date = Form(...),
    invoice_number: str = Form(..., min_length=2, max_length=80),
    warranty_period_months: int = Form(..., ge=1, le=120),
):
    if not request.session.get("username"):
        return RedirectResponse(url="/login", status_code=303)
    admin = _require_admin_html(request, db)
    validate_csrf_token(request, csrf_token)
    owner = db.query(User).filter(User.id == owner_id).first()
    if not owner:
        raise HTTPException(status_code=400, detail="Invalid owner.")
    from app.schemas.product import ProductCreate

    payload = ProductCreate(
        product_name=product_name.strip(),
        brand=brand.strip(),
        model_number=model_number.strip() or None,
        serial_number=serial_number.strip() or None,
        purchase_date=purchase_date,
        invoice_number=invoice_number.strip(),
        warranty_period_months=warranty_period_months,
    )
    ProductService.create_product(db, owner.id, payload)
    return RedirectResponse(url="/admin/products", status_code=303)


@router.post("/admin/products/{product_id}/edit", response_class=HTMLResponse)
def admin_edit_product(
    request: Request,
    product_id: int,
    db: Session = Depends(get_db),
    csrf_token: str = Form(...),
    product_name: str = Form(..., min_length=2, max_length=120),
    brand: str = Form(..., min_length=2, max_length=80),
    model_number: str = Form(default=""),
    serial_number: str = Form(default=""),
    purchase_date: date = Form(...),
    invoice_number: str = Form(..., min_length=2, max_length=80),
    warranty_period_months: int = Form(..., ge=1, le=120),
    status: str = Form(..., min_length=2, max_length=20),
):
    if not request.session.get("username"):
        return RedirectResponse(url="/login", status_code=303)
    _require_admin_html(request, db)
    validate_csrf_token(request, csrf_token)
    AdminService.update_product(
        db,
        product_id,
        product_name=product_name,
        brand=brand,
        model_number=model_number or None,
        serial_number=serial_number or None,
        purchase_date=purchase_date,
        invoice_number=invoice_number,
        warranty_period_months=warranty_period_months,
        status=status.strip().lower(),
    )
    return RedirectResponse(url="/admin/products", status_code=303)


@router.post("/admin/products/{product_id}/delete", response_class=HTMLResponse)
def admin_delete_product(
    request: Request,
    product_id: int,
    db: Session = Depends(get_db),
    csrf_token: str = Form(...),
):
    if not request.session.get("username"):
        return RedirectResponse(url="/login", status_code=303)
    _require_admin_html(request, db)
    validate_csrf_token(request, csrf_token)
    AdminService.delete_product(db, product_id)
    return RedirectResponse(url="/admin/products", status_code=303)


@router.get("/admin/claims", response_class=HTMLResponse)
def admin_claims_page(
    request: Request,
    db: Session = Depends(get_db),
    status: str | None = Query(default=None, max_length=20),
):
    if not request.session.get("username"):
        return RedirectResponse(url="/login", status_code=303)
    admin = _require_admin_html(request, db)
    result = AdminService.list_claims(db, 1, 100, status)
    return templates.TemplateResponse(
        request=request,
        name="admin_claims.html",
        context=_admin_context(
            request,
            admin,
            {"claims": result["items"], "total": result["total"], "status": status or ""},
        ),
    )


@router.post("/admin/claims/{claim_id}/approve", response_class=HTMLResponse)
def admin_approve_claim(
    request: Request,
    claim_id: int,
    db: Session = Depends(get_db),
    csrf_token: str = Form(...),
):
    if not request.session.get("username"):
        return RedirectResponse(url="/login", status_code=303)
    _require_admin_html(request, db)
    validate_csrf_token(request, csrf_token)
    AdminService.set_claim_status(db, claim_id, "approved")
    return RedirectResponse(url="/admin/claims", status_code=303)


@router.post("/admin/claims/{claim_id}/reject", response_class=HTMLResponse)
def admin_reject_claim(
    request: Request,
    claim_id: int,
    db: Session = Depends(get_db),
    csrf_token: str = Form(...),
):
    if not request.session.get("username"):
        return RedirectResponse(url="/login", status_code=303)
    _require_admin_html(request, db)
    validate_csrf_token(request, csrf_token)
    AdminService.set_claim_status(db, claim_id, "rejected")
    return RedirectResponse(url="/admin/claims", status_code=303)


# ---------------------------------------------------------------- JSON ----
@router.get("/api/admin/stats")
def api_admin_stats(
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    stats = AdminService.get_stats(db)
    return {
        "total_customers": stats["total_customers"],
        "total_admins": stats["total_admins"],
        "total_products": stats["total_products"],
        "total_registrations": stats["total_registrations"],
        "total_claims": stats["total_claims"],
        "pending_claims": stats["pending_claims"],
    }


@router.get("/api/admin/customers", response_model=list[UserRead])
def api_admin_customers(
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
    page: int = Query(default=1, ge=1, le=10000),
    page_size: int = Query(default=20, ge=1, le=100),
):
    return AdminService.list_customers(db, page, page_size)["items"]


@router.get("/api/admin/customers/{user_id}", response_model=UserRead)
def api_admin_customer_detail(
    user_id: int,
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    return AdminService.get_customer(db, user_id)


@router.get("/api/admin/products", response_model=list[ProductRead])
def api_admin_products(
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
    page: int = Query(default=1, ge=1, le=10000),
    page_size: int = Query(default=50, ge=1, le=100),
    search: str | None = Query(default=None, max_length=120),
):
    return AdminService.list_products(db, page, page_size, search)["items"]


@router.patch("/api/admin/products/{product_id}", response_model=ProductRead)
def api_admin_update_product(
    product_id: int,
    payload: AdminProductUpdate,
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    return AdminService.update_product(
        db,
        product_id,
        product_name=payload.product_name,
        brand=payload.brand,
        model_number=payload.model_number,
        serial_number=payload.serial_number,
        purchase_date=payload.purchase_date,
        invoice_number=payload.invoice_number,
        warranty_period_months=payload.warranty_period_months,
        status=payload.status.strip().lower(),
    )


@router.delete("/api/admin/products/{product_id}", status_code=204)
def api_admin_delete_product(
    product_id: int,
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    AdminService.delete_product(db, product_id)
    return None


@router.get("/api/admin/claims", response_model=list[WarrantyClaimRead])
def api_admin_claims(
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
    status: str | None = Query(default=None, max_length=20),
):
    return AdminService.list_claims(db, 1, 100, status)["items"]


@router.get("/api/admin/claims/{claim_id}", response_model=WarrantyClaimRead)
def api_admin_claim_detail(
    claim_id: int,
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    return AdminService.get_claim(db, claim_id)


@router.patch("/api/admin/claims/{claim_id}", response_model=WarrantyClaimRead)
def api_admin_update_claim(
    claim_id: int,
    payload: ClaimStatusUpdate,
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    return AdminService.set_claim_status(db, claim_id, payload.status.strip().lower())
