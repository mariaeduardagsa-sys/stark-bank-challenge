from fastapi import FastAPI
from app.webhooks import router

app = FastAPI(title="Stark Bank Challenge", description="Stark Bank Challenge API", version="1.0.0")
app.include_router(router)

@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}