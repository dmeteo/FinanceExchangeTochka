from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi
from api.routers import (
    public,
    balance,
    orders,
    admin
)
from fastapi.middleware.cors import CORSMiddleware

from core.logging_middleware import LoggingMiddleware

app = FastAPI(title="API Tochka", version="0.1.0")

app.add_middleware(LoggingMiddleware)

@app.get("/health")
def health():
    return {"status": "ok"}


def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    openapi_schema = get_openapi(
        title="Peshkin",
        version="1.0.0",
        description="API",
        routes=app.routes,
    )
    openapi_schema["components"]["securitySchemes"] = {
        "ApiKeyAuth": {
            "type": "apiKey",
            "in": "header",
            "name": "Authorization"
        }
    }
    for path in openapi_schema["paths"].values():
        for method in path.values():
            method.setdefault("security", [{"ApiKeyAuth": []}])

    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(public.router)
app.include_router(balance.router)
app.include_router(orders.router)
app.include_router(admin.router)
