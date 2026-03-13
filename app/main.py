from fastapi import FastAPI
from starlette.middleware.sessions import SessionMiddleware
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import os

load_dotenv()

app = FastAPI()

app = FastAPI(
    swagger_ui_parameters={"persistAuthorization": True},
)

app.add_middleware(
    SessionMiddleware,
    secret_key="SECRET_KEY"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=True
)

from app.routers import auth
app.include_router(auth.router)

