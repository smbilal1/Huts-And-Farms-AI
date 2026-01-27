from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
# from app.routers import agent  # REMOVED: Old router causing startup issues
from app.api.v1 import web_chat, webhooks, admin, demo, admin_booking
from app.database import engine
from app import models
import httpx
import json
import base64
import logging
from typing import Optional
from datetime import datetime, timedelta
from app.tasks import start_cleanup_scheduler
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings


models.Base.metadata.create_all(bind=engine)

start_cleanup_scheduler()

app = FastAPI()

# Old agent router removed - functionality moved to app/api/v1/
# app.include_router(agent.router)

# API v1 endpoints
app.include_router(webhooks.router, tags=["Webhooks"])
app.include_router(web_chat.router, prefix="/api")
app.include_router(admin.router, prefix="/api")
app.include_router(admin_booking.router, prefix="/api")
app.include_router(demo.router, prefix="/api", tags=["Demo/Test"])

# Allow all origins (for development)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Change to specific domains in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
registration_store={}

VERIFY_TOKEN = "my_custom_secret_token"
WHATSAPP_TOKEN = settings.META_ACCESS_TOKEN
PHONE_NUMBER_ID = settings.META_PHONE_NUMBER_ID
