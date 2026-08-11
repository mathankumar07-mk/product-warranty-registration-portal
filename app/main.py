from fastapi import FastAPI
from starlette.middleware.sessions import SessionMiddleware

from app.api import auth
from app.core.database import Base, engine
from app.core.settings import settings
import app.models  # noqa: F401  (registers all models)

Base.metadata.create_all(bind=engine)

app = FastAPI(title=settings.APP_NAME)

app.add_middleware(SessionMiddleware, secret_key=settings.SECRET_KEY)

app.include_router(auth.router)
