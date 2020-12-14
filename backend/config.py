from pydantic import BaseSettings


class Config(BaseSettings):

    api_url_prefix: str = '/api'
    db_hostname: str = 'localhost'
    db_port: int = 7687
    db_username: str = 'neo4j'
    db_password: str = 'neo4j'
    auth_token_name: str = 'X-Token'
    cookie_max_age_seconds: int = 60 * 60


config = Config()
del Config
