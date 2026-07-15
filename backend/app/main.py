from fastapi import FastAPI

app = FastAPI(
    title="Consumer Alpha Radar API"
)


@app.get("/")
def home():
    return {
        "message": "Consumer Alpha Radar Backend Running"
    }


@app.get("/health")
def health():
    return {
        "status": "healthy"
    }