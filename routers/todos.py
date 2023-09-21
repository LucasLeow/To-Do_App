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
user_dependency = Annotated[dict, Depends(get_current_user)]

# For To-do Request Validation
class TodoRequest(BaseModel):
    # id not required since primary key auto-increment
    title: str = Field(min_length=3)
    description: str = Field(min_length=3, max_length=100)
    priority: int = Field(gt=0, lt=6)
    complete: bool
    # owner_id provided by JWT

@router.get("/test")
async def test(request: Request):
    return templates.TemplateResponse('register.html', {'request': request})



@router.get("/", status_code=status.HTTP_200_OK)
async def get_all_todos(user: user_dependency, db: db_dependency):
    if user is None:
        raise HTTPException(status_code=401, detail='Authentication Failed')
    return db.query(Todos).filter(Todos.owner_id == user.get('id'))

@router.get('todo/{todo_id}', status_code=status.HTTP_200_OK)
async def get_todo_by_id(user: user_dependency, db: db_dependency, todo_id:int = Path(gt=0)):
    if user is None:
        raise HTTPException(status_code=401, detail='Authentication Failed')

    todo_model = db.query(Todos).filter(Todos.id == todo_id) \
    .filter(Todos.owner_id == user.get('id')).first()

    if todo_model is not None:
        return todo_model

    raise HTTPException(status_code=404, detail='Todo not found')

@router.post('/todo', status_code=status.HTTP_201_CREATED)
async def create_todo(user: user_dependency, db: db_dependency, todo_request: TodoRequest):
    if user is None:
        raise HTTPException(status_code=401, detail='Authentication Failed')

    todo_model = Todos(**todo_request.model_dump(), owner_id = user.get('id'))

    db.add(todo_model)
    db.commit()

@router.put('/todo/{todo_id}', status_code=status.HTTP_204_NO_CONTENT)
async def update_todo(user: user_dependency, db: db_dependency, todo_request: TodoRequest, todo_id: int = Path(gt=0)):
    if user is None:
        raise HTTPException(status_code=401, detail='Authentication Failed')

    todo_model = db.query(Todos).filter(Todos.id == todo_id) \
    .filter(Todos.owner_id == user.get('id')).first()

    if todo_model is None:
        raise HTTPException(status_code=404, detail='todo not found')

    todo_model.title = todo_request.title
    todo_model.description = todo_request.description
    todo_model.priority = todo_request.priority
    todo_model.complete = todo_request.complete

    db.add(todo_model)
    db.commit()

    @router.delete('/todo/{todo_id}', status_code=status.HTTP_204_NO_CONTENT)
    async def delete_todo(user: user_dependency, db: db_dependency, todo_id: int = Path(gt=0)):
        if user is None:
            raise HTTPException(status_code=401, detail='Authentication Failed')

        todo_model = db.query(Todos).filter(Todos.id == todo_id) \
        .filter(Todos.owner_id == user.get('id')).first()

        if todo_model is None:
            raise HTTPException(status_code=404, detail='todo not found')

        db.query(Todos).filter(Todos.id == todo_id) \
        .filter(Todos.owner_id == user.get('id')).delete()

        db.commit()
