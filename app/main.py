
from fastapi import FastAPI

app = FastAPI(
    title="BenchTrack",
    description="Inventory and maintenance management for small workshops.",
    version="0.1.0",
)


@app.get("/")
def home():
    return {
        "message": "Welcome to BenchTrack!",
        "status": "running",
    }


@app.get("/health")
def health_check():
    return {
        "status": "healthy",
    }
