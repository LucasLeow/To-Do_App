from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, Response, Form
from fastapi.templating import Jinja2Templates

from starlette.responses import HTMLResponse, RedirectResponse
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

SECRET_KEY = "76914b3e3a0bafeb34b3024f0f014bb85b5755127f22d6e5e9a7a05f45f5eb84"
ALGO = 'HS256'

bcrypt_context = CryptContext(schemes=['bcrypt'], deprecated='auto')

models.Base.metadata.create_all(bind=database.engine)

oauth2_bearer = OAuth2PasswordBearer(tokenUrl='auth/token')

router = APIRouter(
    prefix='/auth',
    tags=['auth endpoints']
)

# Process form info from login.html
class LoginForm:
    def __init__(self, request: Request):
        self.request: Request = request
        self.username: Optional[str] = None
        self.password: Optional[str] = None

    async def create_oauth_form(self):
        form = await self.request.form()
        self.username = form.get('email')
        self.password = form.get('password')


# Helper Functions
def get_db():
    try:
        db = database.SessionLocal()
        yield db
    finally:
        db.close()

db_dependency = Annotated[Session, Depends(get_db)]

def get_password_hash(password):
    return bcrypt_context.hash(password)

def verify_password(plain_password, hashed_password):
    return bcrypt_context.verify(plain_password, hashed_password)

def authenticate_user(username: str, password: str, db):
    user = db.query(models.Users)\
    .filter(models.Users.username == username).first()

    if not user:
        return False
    if not verify_password(password, user.hashed_password):
        return False
    return user

def create_access_token(username: str, user_id: int,
                        expires_delta: Optional[timedelta]=None):
    encode = {"username": username, "id": user_id}
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)

    encode.update({"exp": expire})
    return jwt.encode(encode, SECRET_KEY, algorithm=ALGO)

async def get_current_user(request: Request):
    try:
        token = request.cookies.get('access_token')
        if token is None:
            return None

        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGO])
        username: str = payload.get('username')
        user_id: int = payload.get('id')
        if username is None or user_id is None:
            logout(request)
        return {'username': username, 'id': user_id}

    except JWTError:
        raise HTTPException(status_code=404, detail='Not Found')


@router.post('/token')
async def login_for_access_token(
        response: Response,
        db: db_dependency,
        form_data: OAuth2PasswordRequestForm = Depends()):
    user = authenticate_user(form_data.username, form_data.password, db)
    if not user:
        return False
    token_expires = timedelta(minutes=60)
    token = create_access_token(user.username, user.id, expires_delta=token_expires)
    response.set_cookie(key='access_token', value=token, httponly=True)
    return {"token": token}

templates = Jinja2Templates(directory='templates')
@router.get("/", response_class=HTMLResponse)
async def authentication_page(request: Request):
    return templates.TemplateResponse('login.html', {'request': request})

@router.post('/', response_class=HTMLResponse)
async def login(request: Request, db: db_dependency):
    try:
        form = LoginForm(request)
        await form.create_oauth_form()
        response = RedirectResponse(url='/todos',status_code=status.HTTP_302_FOUND)

        validate_user_cookie = await login_for_access_token(response=response, form_data=form, db=db)

        if not validate_user_cookie:
            msg = 'incorrect username or password'
            return templates.TemplateResponse('login.html', {'request': request, 'msg': msg})

        return response

    except HTTPException:
        msg = 'unknown error'
        return templates.TemplateResponse('login.html', {'request':request,'msg': msg})

@router.get('/logout')
async def logout(request: Request):
    msg = "logout successful"
    response = templates.TemplateResponse('login.html', {'request': request, 'msg': msg})
    response.delete_cookie(key='access_token')
    return response

@router.get('/register', response_class=HTMLResponse)
async def register(request:  Request):
    return templates.TemplateResponse('register.html', {'request': request})

@router.post('/register', response_class=HTMLResponse)
async def register_user(db: db_dependency, request: Request,
                        email: str = Form(...),
                        username: str = Form(...),
                        firstname: str = Form(...),
                        lastname: str = Form(...),
                        password: str = Form(...),
                        password2: str = Form(...),
                        ):

    username_already_exist = db.query(models.Users).filter(models.Users.username == username).first()
    email_already_exist = db.query(models.Users).filter(models.Users.email == email).first()

    if password != password2 or username_already_exist is not None or email_already_exist is not None:
        msg = "invalid registration request"
        return templates.TemplateResponse('register.html', {'request': request, 'msg': msg})

    user_model = models.Users()
    user_model.username = username
    user_model.email = email
    user_model.first_name = firstname
    user_model.last_name = lastname

    hash_password = get_password_hash(password)
    user_model.hashed_password = hash_password

    user_model.is_active = True

    db.add(user_model)
    db.commit()

    msg = 'user successfully created'
    return templates.TemplateResponse('login.html', {'request': request, 'msg': msg})


