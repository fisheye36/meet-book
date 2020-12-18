from contextlib import suppress

from fastapi import FastAPI

from backend.api import api
from backend.config import config
from frontend.api import frontend_api


app = FastAPI(title='MeetBook')
app.include_router(api, prefix=config.api_url_prefix)
app.include_router(frontend_api)


@app.get('/')
async def get_root():
    return {'hello': 'world'}


if __name__ == '__main__':
    with suppress(ImportError):
        import uvicorn
        uvicorn.run('backend.main:app', reload=True)
