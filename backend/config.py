from pathlib import Path

from jinja2 import Environment, FileSystemLoader
from pydantic import BaseSettings, DirectoryPath


class Config(BaseSettings):

    api_url_prefix: str = '/api'
    db_hostname: str = 'localhost'
    db_port: int = 7687
    db_username: str = 'neo4j'
    db_password: str = 'neo4j'
    auth_token_name: str = 'X-Token'
    auth_token_duration_seconds: int = 60 * 60 * 24  # TODO: lower to one day in production
    cookie_max_age_seconds: int = 60 * 60 * 24  # TODO: lower to one day in production
    secret_key: str = 'secret'  # TODO: change in production
    templates_location: DirectoryPath = (Path(__file__).parent / '../frontend/templates').resolve()


config = Config()
del Config

jinja = Environment(loader=FileSystemLoader(config.templates_location))
