from typing import Annotated
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session


from starlette import status
from starlette.responses import RedirectResponse
from fastapi import APIRouter, Depends, HTTPException, Request, Form
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse

from persistence import models
from persistence.database import engine, SessionLocal

from .auth import get_current_user, verify_password, get_password_hash
from passlib.context import CryptContext

router = APIRouter(
    prefix='/users',
    tags=['users'],
    responses={404: {'description': 'Not Found'}}
)

models.Base.metadata.create_all(bind=engine)

bcrypt_context = CryptContext(schemes=['bcrypt'], deprecated='auto')

templates = Jinja2Templates(directory='templates')

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

db_dependency = Annotated[Session, Depends(get_db)]

class UserVerificationRequest(BaseModel):
    username: str
    password: str
    new_password: str

@router.get('/edit-password', response_class=HTMLResponse)
async def edit_user_password(request: Request):
    user = await get_current_user(request)

    if user is None:
        return RedirectResponse(url='/auth', status_code=status.HTTP_302_FOUND)

    return templates.TemplateResponse('edit-user-password.html', {'request': request, 'user': user})


@router.post('/edit-password', response_class=HTMLResponse)
async def user_password_change(request: Request, db: db_dependency,
                               username: str = Form(...),
                               password: str = Form(...),
                               password2: str = Form(...)):
    user = await get_current_user(request)
    if user is None:
        return RedirectResponse(url='/auth', status_code=status.HTTP_302_FOUND)

    user_data = db.query(models.Users).filter(models.Users.username == username).first()
    msg = "Invalid username or password"

    if user_data is None:
        return templates.TemplateResponse('edit-user-password.html', {'request': request, 'msg': msg})


    if user_data is not None:
        if username == user_data.username and verify_password(password, user_data.hashed_password):
            user_data.hashed_password = get_password_hash(password2)
            db.add(user_data)
            db.commit()
            msg = 'password updated'
            RedirectResponse(url='/auth/logout', status_code=status.HTTP_302_FOUND)

        return templates.TemplateResponse('edit-user-password.html', {'request': request, 'msg': msg})



