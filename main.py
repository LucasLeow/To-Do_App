from fastapi import FastAPI
import models
from database import engine
from routers import auth

app = FastAPI()

app.include_router(auth.router)


