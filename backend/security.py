from fastapi import Cookie, HTTPException, status

from backend.config import config
from backend.database import database
from backend.models import UserIn, UserOut


def create_auth_token(user: UserIn) -> str:
    return f'{user.username}_-_{user.password}'


def get_logged_user(token: str = Cookie(..., alias=config.auth_token_name)) -> UserOut:
    user = get_user_from_token(token)
    return user


def get_user_from_token(token: str) -> UserOut:
    parts = token.split('_-_', 1)
    if len(parts) < 2:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail='Wrong credentials')

    username = parts[0]
    with database.session as s:
        results = s.run('MATCH (n:User) WHERE n.username = $username RETURN n', username=username).single()
        if not results:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail='Not found')

        user = results['n']
        return UserOut(
            username=user['username'],
        )
