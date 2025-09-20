from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates

router = APIRouter()
templates = Jinja2Templates("pages")

version = "v2025.09.20"


@router.get("/", include_in_schema=False)
def index(request: Request):
    return templates.TemplateResponse(
        request, "index.html", {"request": request, "version": "v2025.09.20"}
    )
