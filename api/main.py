# Entry point for the FastAPI app.
#
# Run it with:
#     cd hackathon-starter-kit/api
#     pip install -r requirements.txt
#     uvicorn main:app --reload
#
# Then open http://127.0.0.1:8000 in your browser.

from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from database import init_db
from routers import ai, auth

app = FastAPI(title="Hackathon Starter Kit API")


@app.on_event("startup")
def on_startup():
    # Create the database tables (if they don't exist yet) as soon as
    # the app starts.
    init_db()


# Register routers here. Add new ones the same way as you build out
# more features, e.g. app.include_router(chat.router).
app.include_router(auth.router)
app.include_router(ai.router)

# Serve the frontend (the "client" folder) as static files. This lets
# the whole app - frontend + API - run from a single server on one
# port, with no CORS configuration needed.
CLIENT_DIR = Path(__file__).resolve().parent.parent / "client"
app.mount("/", StaticFiles(directory=CLIENT_DIR, html=True), name="client")
