from fastapi import APIRouter
from starlette.responses import HTMLResponse

from backend.main import api
from backend.config import jinja, config


frontend_api = APIRouter()


@frontend_api.get('/login', response_class=HTMLResponse)
def login_page() -> str:
    template = jinja.get_template('login.html')
    return template.render(login_endpoint=config.api_url_prefix + api.url_path_for('login'))
