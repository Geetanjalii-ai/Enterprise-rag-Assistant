from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.api.v1.auth import limiter
from app.api.v1.router import api_v1_router
from app.core.config import get_settings
from app.core.logging import setup_logging

setup_logging()
settings = get_settings()

app = FastAPI(
    title="Enterprise RAG Assistant API",
    version="0.3.0",
    description="Role-aware Enterprise RAG Assistant API with multi-department ACL enforcement",
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)  # type: ignore[arg-type]

# Strict CORS for frontend client (supporting both localhost and 127.0.0.1 on any dev port)
app.add_middleware(
    CORSMiddleware,
    allow_origins=list(
        set(
            settings.cors_origin_list
            + [
                "http://localhost:5173",
                "http://127.0.0.1:5173",
                "http://localhost:3000",
                "http://127.0.0.1:3000",
            ]
        )
    ),
    allow_origin_regex=r"^https?://(localhost|127\.0\.0\.1)(:[0-9]+)?$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_v1_router)


@app.get("/health")
def health():
    return {"status": "ok", "app_env": settings.APP_ENV}
