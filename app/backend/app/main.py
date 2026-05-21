from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import auth, projects

app = FastAPI(title="AI Construction Estimator")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3036"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(projects.router)
