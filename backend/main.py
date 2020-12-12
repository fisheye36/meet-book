from contextlib import suppress

from fastapi import FastAPI

from backend.api import api
from backend.config import config


app = FastAPI()
app.include_router(api, prefix=config.api_url_prefix)


@app.get('/')
async def get_root():
    return {'hello': 'world'}


if __name__ == '__main__':
    with suppress(ImportError):
        import uvicorn
        uvicorn.run('backend.main:app', reload=True)
