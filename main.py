from fastapi import FastAPI
from routers import auth, todos, admin, users

app = FastAPI()

app.include_router(auth.router)
app.include_router(todos.router)
app.include_router(admin.router)
app.include_router(users.router)
