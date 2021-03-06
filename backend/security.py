import json
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import Cookie, Depends, HTTPException, Request, status
from fastapi.security.http import HTTPAuthorizationCredentials, HTTPBase
from jwcrypto import jwk, jwt
from jwcrypto.common import JWException

from backend.config import config
from backend.database import database
from backend.models import UserIn, UserOut


class HttpCookieToken(HTTPBase):

    def __call__(self, request: Request):
        token = request.cookies.get(config.auth_token_name)
        if not token:
            if self.auto_error:
                raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail='Token missing')
            else:
                return None
        return HTTPAuthorizationCredentials(scheme='', credentials=token)


auth_scheme = HttpCookieToken(scheme='bearer')


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


def get_user_if_logged(auth_token: Optional[str] = Cookie(None, alias=config.auth_token_name)) -> Optional[UserOut]:
    return get_user_from_token(auth_token) if auth_token is not None else None


def get_logged_user(auth_credentials: HTTPAuthorizationCredentials = Depends(auth_scheme)) -> UserOut:
    token = auth_credentials.credentials
    if (user := get_user_from_token(token)) is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail='Token invalid or expired')
    return user


def get_user_from_token(token: str) -> Optional[UserOut]:
    key = _get_token_key()
    try:
        decoded_token = jwt.JWT(jwt=token, key=key)
    except JWException:
        return None
    else:
        claims = json.loads(decoded_token.claims)
        username = claims.get('sub', '')

    with database.session as s:
        if not (results := s.run('MATCH (n:User) WHERE n.username = $username RETURN n', username=username).single()):
            return None

        db_user = results['n']
        return UserOut(
            **db_user,
            url='/',
        )
