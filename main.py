from fastapi import FastAPI
from routers import auth, todos, admin

app = FastAPI()

app.include_router(auth.router)
app.include_router(todos.router)
app.include_router(admin.router)

