from fastapi import Request
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles

# Constants
ALLOWED_MODELS = ["flux-pro-1.1", "flux-pro", "flux-dev"]

# Initialize templates
templates = Jinja2Templates(directory="templates")

async def get_index_page(request: Request):
    """Render the main page"""
    return templates.TemplateResponse(
        "index.html",
        {"request": request, "models": ALLOWED_MODELS}
    ) 