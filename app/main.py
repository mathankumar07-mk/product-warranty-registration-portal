from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware

from app.api import auth
from app.core.database import Base, engine
from app.core.settings import settings
import app.models  # noqa: F401  (registers all models)

Base.metadata.create_all(bind=engine)

app = FastAPI(title=settings.APP_NAME)

cors_origins = [
	origin.strip().rstrip("/")
	for origin in settings.CORS_ORIGINS.split(",")
	if origin.strip()
]
if "*" in cors_origins:
	raise ValueError("CORS_ORIGINS must contain explicit origins, not '*'.")

app.add_middleware(
	CORSMiddleware,
	allow_origins=cors_origins,
	allow_credentials=True,
	allow_methods=["*"],
	allow_headers=["*"],
)
app.add_middleware(SessionMiddleware, secret_key=settings.SECRET_KEY)

app.include_router(auth.router)


@app.get("/health", tags=["health"])
def health_check():
	return {"status": "ok"}
