from fastapi import FastAPI

app = FastAPI(title="Banking Backend API")

@app.get("/health")
def health_check():
    return {"status": "ok"}
