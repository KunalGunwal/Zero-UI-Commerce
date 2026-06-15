from fastapi import FastAPI
from app.api.routes import router

# Initialize the core FastAPI application
app = FastAPI(title="Amazon Hackon Grocery Bot")

# Attach the webhook routes we built in routes.py
app.include_router(router)

# A quick health check endpoint to prove the server is running
@app.get("/")
def health_check():
    return {"status": "healthy", "message": "Grocery Bot is Online!"}