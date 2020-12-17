import json
from datetime import datetime, timedelta, timezone

from fastapi import Cookie, HTTPException, status
from jwcrypto import jwk, jwt
from jwcrypto.common import JWException

from backend.config import config
from backend.database import database
from backend.models import UserIn, UserOut


def create_auth_token(user: UserIn) -> str:
    key = _get_token_key()
    try:
        jwt_token = jwt.JWT(
            header={
                'alg': 'HS256',
                'typ': 'JWT',
            },
            claims={
                'sub': user.username,
                'iat': (now := datetime.now(timezone.utc)).timestamp(),
                'exp': (now + timedelta(seconds=config.auth_token_duration_seconds)).timestamp(),
            },
        )
        jwt_token.make_signed_token(key)
    except JWException:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail='Token encoding fail') from None
    else:
        return jwt_token.serialize()


def _get_token_key() -> jwk.JWK:
    try:
        return jwk.JWK(kty='oct', k=config.secret_key)
    except JWException:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail='Token generation fail') from None


def get_logged_user(token: str = Cookie(..., alias=config.auth_token_name)) -> UserOut:
    user = get_user_from_token(token)
    return user


def get_user_from_token(token: str) -> UserOut:
    key = _get_token_key()
    try:
        decoded_token = jwt.JWT(jwt=token, key=key)
    except JWException:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail='Token invalid or expired')
    else:
        claims = json.loads(decoded_token.claims)
        username = claims.get('sub', '')

    with database.session as s:
        results = s.run('MATCH (n:User) WHERE n.username = $username RETURN n', username=username).single()
        if not results:
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail='Wrong credentials')

        db_user = results['n']
        return UserOut(
            **db_user,
            url='/',
        )
