
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from backend.file_routes import router as file_router
from backend.chat_routes import router as chat_router


app = FastAPI(title="DataChat backend")


# ---------------------------------------------------------
# SERVE GENERATED CHARTS
# ---------------------------------------------------------

app.mount(
    "/exports",
    StaticFiles(directory="exports"),
    name="exports"
)


# ---------------------------------------------------------
# API ROUTES
# ---------------------------------------------------------

app.include_router(
    file_router,
    prefix="/api",
    tags=["File Service"]
)

app.include_router(
    chat_router,
    prefix="/api",
    tags=["Chat Service"]
)
# @app.get("/")
# async def root():
#     return {
#         "message": "DataChat AI API is running"
#     }