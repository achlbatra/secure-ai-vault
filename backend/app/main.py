from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import auth_routers as auth

app = FastAPI(title="Secure AI Vault")

app.include_router(auth.router)

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
