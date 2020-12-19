from datetime import datetime, timezone
from functools import lru_cache

import requests
from fastapi import APIRouter
from starlette.responses import HTMLResponse

from backend.api import get_posts
from backend.config import config, jinja
from backend.main import api
from backend.models import UserOut


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


@frontend_api.get('/', response_class=HTMLResponse)
def index_page() -> str:
    posts = get_posts()
    for post in posts:
        author = _get_user_from_api(f'http://localhost:8000{post.author}')
        post.author_username = author.username
        post.date = datetime.fromtimestamp(int(post.timestamp) / 1000, timezone.utc).strftime('%d/%m/%Y %H:%M:%S %Z')

    template = jinja.get_template('index.html')
    return template.render(
        posts=posts,
    )


@lru_cache(maxsize=128)
def _get_user_from_api(url: str) -> UserOut:
    response = requests.get(url)
    return UserOut(**response.json())
