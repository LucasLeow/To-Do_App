from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request
from starlette import status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from persistence import database, models
from persistence import models

from passlib.context import CryptContext
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer
from datetime import timedelta, datetime
from jose import jwt, JWTError

from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

templates = Jinja2Templates(directory='templates')

router = APIRouter(
    prefix='/auth',
    tags=['auth endpoints']
)

SECRET_KEY = "76914b3e3a0bafeb34b3024f0f014bb85b5755127f22d6e5e9a7a05f45f5eb84"
ALGO = 'HS256'

bcrypt_context = CryptContext(schemes=['bcrypt'], deprecated='auto')
oauth2_bearer = OAuth2PasswordBearer(tokenUrl='auth/token')

class CreateUserRequest(BaseModel):
    #user_id auto increment
    username: str
    email: str
    first_name: str
    last_name: str
    password: str
    role: str
    #todo_id auto increment

class Token(BaseModel):
    access_token: str
    token_type: str


def get_db():
    db = database.SessionLocal()
    try:
        yield db
    finally:
        db.close()


def authenticate_user(username: str, password: str, db):
    user = db.query(models.Users).filter(models.Users.username == username).first()
    if not user:
        return False

    if not bcrypt_context.verify(password, user.hashed_password):
        return False

    return user

def create_access_token(username: str, user_id: int, role: str, expires_delta: timedelta):
    encode = {
        'username': username,
        'id': user_id,
        'role': role
    }

    expires = datetime.utcnow() + expires_delta
    encode.update({
        'exp': expires
    })

    return jwt.encode(encode, SECRET_KEY, algorithm=ALGO)

async def get_current_user(token: Annotated[str, Depends(oauth2_bearer)]):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGO])
        username: str = payload.get('username')
        user_id: int = payload.get('id')
        user_role: str = payload.get('role')

        if username is None or user_id is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='could not validate user')

        return {'username': username, 'id': user_id, 'user_role': user_role}

    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='could not validate user')


db_dependency = Annotated[Session, Depends(get_db)]

@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_user(db: db_dependency, create_user_request: CreateUserRequest):
    create_user_model = models.Users(
        email = create_user_request.email,
        username = create_user_request.username,
        first_name = create_user_request.first_name,
        last_name = create_user_request.last_name,
        role = create_user_request.role,
        hashed_password = bcrypt_context.hash(create_user_request.password),
        is_active = True
    )

    db.add(create_user_model)
    db.commit()

@router.get("/", response_class=HTMLResponse)
async def login_authentication(request: Request):
    return templates.TemplateResponse("login.html", {'request': request})

@router.get("/register", response_class=HTMLResponse)
async def login_authentication(request: Request):
    return templates.TemplateResponse("register.html", {'request': request})

@router.post("/token", response_model=Token)
async def login_for_access_token(
        form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
        db: db_dependency
):
    user = authenticate_user(form_data.username, form_data.password, db)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='could not validate user')

    token = create_access_token(user.username, user.id, user.role, timedelta(minutes=20))
    return {'access_token': token, 'token_type': 'bearer'}

