import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import audit as audit_api
from app.api import auth as auth_api
from app.api import dossiers as dossiers_api
from app.api import knowledge as knowledge_api
from app.api import me as me_api
from app.api import tenants as tenants_api
from app.core.config import settings
from app.webhooks import web as web_webhook
from app.webhooks import whatsapp as whatsapp_webhook

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield


app = FastAPI(
    title="MA2E - Plateforme Digitale d'Identification",
    description="Plateforme d'identification des sociétaires MA2E (Mutuelle des Agents de l'Eau et de l'Électricité). Architecture multi-tenant pour extension groupe.",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_api.router)
app.include_router(me_api.router)
app.include_router(tenants_api.router)
app.include_router(dossiers_api.router)
app.include_router(knowledge_api.router)
app.include_router(audit_api.router)
app.include_router(web_webhook.router)
app.include_router(whatsapp_webhook.router)


@app.get("/")
async def root():
    return {
        "service": "ma2e-identification-platform",
        "env": settings.app_env,
        "status": "ok",
    }


@app.get("/health")
async def health():
    return {"status": "healthy"}
