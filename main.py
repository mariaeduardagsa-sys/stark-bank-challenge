from fastapi import FastAPI

app = FastAPI(title="Stark Bank Challenge", description="Stark Bank Challenge API", version="1.0.0")

@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}