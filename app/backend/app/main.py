from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import auth, projects, rates, report, stream


@asynccontextmanager
async def lifespan(app):
    from concurrent.futures import ProcessPoolExecutor
    projects._executor = ProcessPoolExecutor(max_workers=2)
    yield
    if projects._executor:
        projects._executor.shutdown(wait=False)


app = FastAPI(title="AI Construction Estimator", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3036",
        "http://116.202.210.102:20261"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(projects.router)
app.include_router(stream.router)
app.include_router(report.router)
app.include_router(rates.router)
