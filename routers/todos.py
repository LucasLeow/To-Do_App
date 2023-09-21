import sys

from typing import Annotated
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from fastapi import APIRouter, Depends, Path, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from starlette import status

sys.path.append('../FullStackToDoApp')
from persistence.models import *
from persistence.database import SessionLocal

from .auth import get_current_user

router = APIRouter(
    prefix='/todos',
    tags=['todos endpoints']
)

templates = Jinja2Templates(directory='templates')

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

db_dependency = Annotated[Session, Depends(get_db)]

@router.get("/", response_class=HTMLResponse)
async def read_all_todo_by_user(request: Request, db: db_dependency):
    todos = db.query(Todos).filter(Todos.owner_id == 1).all()
    return templates.TemplateResponse("home.html", {"request": request, 'todos': todos})

@router.get("/add-todo", response_class=HTMLResponse)
async def add_new_todo(request: Request):
    return templates.TemplateResponse("add-todo.html", {'request': request})

@router.get("/edit-todo/{todo_id}", response_class=HTMLResponse)
async def edit_todo(request: Request):
    return templates.TemplateResponse("edit-todo.html", {'request': request})