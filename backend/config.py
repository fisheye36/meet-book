from pydantic import BaseSettings


class Config(BaseSettings):

    api_url_prefix: str = '/api'


config = Config()
del Config
