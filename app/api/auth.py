from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models import User
from app.schemas.user import UserCreate
from app.services import auth as auth_service

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


def get_logged_in_user(request: Request, db: Session = Depends(get_db)) -> User | None:
    username = request.session.get("username")
    if not username:
        return None
    return db.query(User).filter(User.username == username).first()


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
    request: Request, user: User | None = Depends(get_logged_in_user)
):
    if not user:
        return RedirectResponse(url="/login", status_code=303)
    return templates.TemplateResponse(
        request=request, name="dashboard.html", context={"user": user}
    )


@router.get("/logout", response_class=HTMLResponse)
def logout(request: Request):
    request.session.pop("username", None)
    request.session.clear()
    return RedirectResponse(url="/login", status_code=303)
