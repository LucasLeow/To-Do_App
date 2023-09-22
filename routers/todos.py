import sys

from typing import Annotated
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from fastapi import APIRouter, Depends, Path, HTTPException, Request, Form
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from starlette import status
from starlette.responses import RedirectResponse

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

# path must be same name as html name for form (add-todo.html)
@router.post("/add-todo", response_class=HTMLResponse)
async def create_todo( db: db_dependency, request: Request, title: str = Form(...), description: str = Form(...),
                      priority: int = Form(...)):
    todo_model = Todos()
    todo_model.title = title
    todo_model.description = description
    todo_model.priority = priority
    todo_model.complete = False
    todo_model.owner_id = 1 # implement dynamically with Auth later

    db.add(todo_model)
    db.commit()

    return RedirectResponse(url='/todos', status_code=status.HTTP_302_FOUND)


@router.get("/edit-todo/{todo_id}", response_class=HTMLResponse)
async def edit_todo(request: Request, db: db_dependency, todo_id: int):
    todo = db.query(Todos).filter(Todos.id == todo_id).first()

    return templates.TemplateResponse("edit-todo.html", {'request': request, 'todo': todo})


@router.post('/edit-todo/{todo_id}', response_class=HTMLResponse)
async def edit_todo_commit(request: Request, db: db_dependency, todo_id: int, title: str = Form(...),
                           description: str = Form(...), priority: int = Form(...)):
    todo_model = db.query(Todos).filter(Todos.id == todo_id).first()

    todo_model.title = title
    todo_model.description = description
    todo_model.priority = priority

    db.add(todo_model)
    db.commit()

    return RedirectResponse(url='/todos', status_code=status.HTTP_302_FOUND)


@router.get('/delete/{todo_id}')
async def delete_todo(request: Request, todo_id: int, db: db_dependency):
    todo_model = db.query(Todos).filter(Todos.id == todo_id) \
    .filter(Todos.owner_id == 1).first()

    if todo_model is None:
        return RedirectResponse(url="/todos", status_code=status.HTTP_404_NOT_FOUND)

    db.query(Todos).filter(Todos.id == todo_id).delete()
    db.commit()

    return RedirectResponse(url='/todos', status_code=status.HTTP_302_FOUND)

@router.get('/complete/{todo_id}', response_class=HTMLResponse)
async def complete_todo(request: Request, todo_id: int, db: db_dependency):
    todo = db.query(Todos).filter(Todos.id == todo_id).first()

    todo.complete = not todo.complete

    db.add(todo)
    db.commit()

    return RedirectResponse(url="/todos", status_code=status.HTTP_302_FOUND)
