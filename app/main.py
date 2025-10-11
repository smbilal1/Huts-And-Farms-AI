from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from app.routers import wati_webhook, web_routes
from app.routers import agent 
from app.database import engine
from app.chatbot import models
import httpx
import json
import base64
import logging
import os
from dotenv import load_dotenv
from typing import Optional
from datetime import datetime, timedelta
from app.scheduler import start_cleanup_scheduler
from fastapi.middleware.cors import CORSMiddleware


models.Base.metadata.create_all(bind=engine)

start_cleanup_scheduler()

app = FastAPI()



app.include_router(agent.router)  
app.include_router(wati_webhook.router)
app.include_router(web_routes.router, prefix="/api", tags=["Web Chat"])

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

load_dotenv()

VERIFY_TOKEN = "my_custom_secret_token"
WHATSAPP_TOKEN = os.getenv("META_ACCESS_TOKEN")
PHONE_NUMBER_ID = os.getenv("META_PHONE_NUMBER_ID")
