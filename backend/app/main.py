from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import auth_routers as auth
from app.routers import file_routers as file
from app.routers import users as user
from app.routers import sanitize_routers as sanitize
from app.routers import dashboard_routers as dashboard_route
from app.core.database import Base, engine
from app.models import document, dashboard  # import models so SQLAlchemy knows them

# Create tables
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Secure AI Vault")

app.include_router(auth.router)
app.include_router(file.router)
app.include_router(user.router)
app.include_router(sanitize.router)
app.include_router(dashboard_route.router)

origins = {
    "http://localhost:3000",
    "http://localhost:5173",
}

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/app_health")
async def read_root():
    return {"Backend": "Healthy"}
