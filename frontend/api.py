from fastapi import APIRouter
from starlette.responses import HTMLResponse

from backend.main import api
from backend.config import jinja, config


frontend_api = APIRouter()


@frontend_api.get('/login', response_class=HTMLResponse)
def login_page() -> str:
    template = jinja.get_template('login.html')
    return template.render(login_endpoint=config.api_url_prefix + api.url_path_for('login'))


@frontend_api.get('/register', response_class=HTMLResponse)
def register_page() -> str:
    template = jinja.get_template('register.html')
    return template.render(
        register_endpoint=config.api_url_prefix + api.url_path_for('create_user'),
        login_endpoint=frontend_api.url_path_for('login_page'),
    )
