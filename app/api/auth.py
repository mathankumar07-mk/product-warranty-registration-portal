from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models import User
from app.schemas.claim import WarrantyClaimCreate, WarrantyClaimRead
from app.schemas.product import ProductCreate, ProductRead
from app.schemas.user import UserCreate, UserRead
from app.services import auth as auth_service
from app.services.product import ProductService

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


def get_logged_in_user(request: Request, db: Session = Depends(get_db)) -> User | None:
    username = request.session.get("username")
    if not username:
        return None
    normalized = str(username).strip()
    if not normalized:
        return None
    return db.query(User).filter(func.lower(User.username) == normalized.lower()).first()


def get_current_user(
    request: Request, db: Session = Depends(get_db)
) -> User:
    user = get_logged_in_user(request, db)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user


@router.get("/", response_class=HTMLResponse)
def home(request: Request, user: User | None = Depends(get_logged_in_user)):
    if user:
        return RedirectResponse(url="/dashboard", status_code=303)
    return RedirectResponse(url="/login", status_code=303)


@router.get("/login", response_class=HTMLResponse)
def login_page(
    request: Request, user: User | None = Depends(get_logged_in_user)
):
    if user:
        return RedirectResponse(url="/dashboard", status_code=303)
    return templates.TemplateResponse(
        request=request, name="login.html", context={"error": None}
    )


@router.post("/login", response_class=HTMLResponse)
def login_submit(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    try:
        user = auth_service.authenticate_user(db, username, password)
    except auth_service.InvalidCredentialsError as exc:
        return templates.TemplateResponse(
            request=request,
            name="login.html",
            context={"error": str(exc)},
            status_code=400,
        )

    request.session["username"] = user.username
    return RedirectResponse(url="/dashboard", status_code=303)


@router.get("/register", response_class=HTMLResponse)
def register_page(
    request: Request, user: User | None = Depends(get_logged_in_user)
):
    if user:
        return RedirectResponse(url="/dashboard", status_code=303)
    return templates.TemplateResponse(
        request=request,
        name="register.html",
        context={"error": None, "form": {}},
    )


@router.post("/register", response_class=HTMLResponse)
def register_submit(
    request: Request,
    username: str = Form(...),
    email: str = Form(...),
    full_name: str = Form(""),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    form_data = {
        "username": username.strip(),
        "email": email.strip(),
        "full_name": full_name.strip(),
        "password": password,
    }
    user_data = UserCreate(**form_data)
    try:
        auth_service.register_user(db, user_data)
    except auth_service.DuplicateUserError as exc:
        return templates.TemplateResponse(
            request=request,
            name="register.html",
            context={"error": str(exc), "form": form_data},
            status_code=400,
        )

    return RedirectResponse(url="/login?registered=1", status_code=303)


@router.get("/dashboard", response_class=HTMLResponse)
def dashboard(
    request: Request,
    user: User | None = Depends(get_logged_in_user),
    db: Session = Depends(get_db),
):
    if not user:
        return RedirectResponse(url="/login", status_code=303)
    products = ProductService.list_user_products(db, user.id)
    claims = ProductService.list_user_claims(db, user.id)
    return templates.TemplateResponse(
        request=request,
        name="dashboard.html",
        context={"user": user, "products": products, "claims": claims},
    )


@router.get("/api/me", response_model=UserRead)
def get_me(current_user: User = Depends(get_current_user)):
    return current_user


@router.get("/api/products", response_model=list[ProductRead])
def list_products(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return ProductService.list_user_products(db, current_user.id)


@router.get("/api/products/{product_id}", response_model=ProductRead)
def get_product(
    product_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return ProductService.get_user_product(db, current_user.id, product_id)


@router.post("/api/products", response_model=ProductRead, status_code=201)
def create_product(
    payload: ProductCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return ProductService.create_product(db, current_user.id, payload)


@router.get("/api/claims", response_model=list[WarrantyClaimRead])
def list_claims(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return ProductService.list_user_claims(db, current_user.id)


@router.get("/api/claims/{claim_id}", response_model=WarrantyClaimRead)
def get_claim(
    claim_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return ProductService.get_user_claim(db, current_user.id, claim_id)


@router.post("/api/claims", response_model=WarrantyClaimRead, status_code=201)
def create_claim(
    payload: WarrantyClaimCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return ProductService.create_claim(db, current_user.id, payload)


@router.get("/logout", response_class=HTMLResponse)
def logout(request: Request):
    request.session.pop("username", None)
    request.session.clear()
    return RedirectResponse(url="/login", status_code=303)
