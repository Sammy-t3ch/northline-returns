from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import os

load_dotenv()

from app.routers import refunds

app = FastAPI(
    title="Northline Care — Refund API",
    description="Policy-gated AI refund assistant powered by NVIDIA NIM",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(refunds.router)


@app.get("/")
async def root():
    return {
        "name": "Northline Care Refund API",
        "docs": "/docs",
        "health": "/api/health",
    }
