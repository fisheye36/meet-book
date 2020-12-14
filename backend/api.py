from typing import List

from fastapi import APIRouter, HTTPException, Response, status
from neo4j.exceptions import ConstraintError

from backend.config import config
from backend.database import database
from backend.models import CommentIn, CommentOut, PostIn, PostOut, UserIn, UserOut
from backend.security import create_auth_token


users_api = APIRouter(tags=['users'])


@users_api.post('/login', response_model=UserOut, tags=['authentication'])
def login(response: Response, user: UserIn):
    with database.session as s:
        results = s.run('MATCH (n:User) WHERE n.username = $username AND n.password = $password RETURN n',
                        username=user.username, password=user.password).single()
        if not results:
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail='Wrong credentials')

        token = create_auth_token(user)
        response.set_cookie(
            key=config.auth_token_name,
            value=token,
            max_age=config.cookie_max_age_seconds,
        )

        user = results['n']
        return UserOut(**user)


@users_api.post('/users', response_model=UserOut)
def create_user(user: UserIn):
    with database.session as s:
        try:
            s.run('CREATE (n:User { username: $username, password: $password })', user.dict())
        except ConstraintError:
            raise HTTPException(status.HTTP_406_NOT_ACCEPTABLE, detail='User already exists') from None
        else:
            return user


@users_api.get('/users/{username}', response_model=UserOut)
def get_specific_user(username: str):
    with database.session as s:
        results = s.run('MATCH (n:User) WHERE n.username = $username RETURN n', username=username).single()
        if not results:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail='Not found')

        user = results['n']
        return UserOut(**user)


@users_api.get('/users', response_model=List[UserOut])
def get_users():
    with database.session as s:
        users: List[UserOut] = []
        for user in s.run('MATCH (n:User) RETURN n').value():
            users.append(UserOut(
                username=user['username'],
            ))
        return users


posts_api = APIRouter(tags=['posts'])


@posts_api.post('/posts', response_model=PostOut)
def create_post(post: PostIn):
    return PostOut(
        **post.dict(),
        user=config.api_url_prefix + api.url_path_for('get_specific_user', username='PostAuthor'),
    )


@posts_api.get('/posts/{post_id}', response_model=PostOut)
def get_specific_post(post_id: int):
    return PostOut(
        content='ExamplePost',
        likes=4,
        user=config.api_url_prefix + api.url_path_for('get_specific_user', username='ExampleUser'),
        comments=[
            config.api_url_prefix + api.url_path_for('get_specific_comment', comment_id=1),
            config.api_url_prefix + api.url_path_for('get_specific_comment', comment_id=2),
        ],
    )


@posts_api.get('/posts', response_model=List[PostOut])
def get_posts():
    return [
        PostOut(
            content='FirstExamplePost',
            user=config.api_url_prefix + api.url_path_for('get_specific_user', username='FirstAuthor'),
        ),
        PostOut(
            content='SecondExamplePost',
            likes=4,
            user=config.api_url_prefix + api.url_path_for('get_specific_user', username='SecondAuthor'),
            comments=[
                config.api_url_prefix + api.url_path_for('get_specific_comment', comment_id=1),
                config.api_url_prefix + api.url_path_for('get_specific_comment', comment_id=2),
            ],
        ),
    ]


comments_api = APIRouter(tags=['comments'])


@comments_api.post('/posts/{post_id}/comments', response_model=CommentOut)
def create_comment(post_id: int, comment: CommentIn):
    return CommentOut(
        **comment.dict(),
        user=config.api_url_prefix + api.url_path_for('get_specific_user', username='ExampleUser'),
        post=config.api_url_prefix + api.url_path_for('get_specific_post', post_id=post_id),
    )


@comments_api.get('/comments/{comment_id}', response_model=CommentOut)
def get_specific_comment(comment_id: int):
    return CommentOut(
        content='ExampleCommentContent',
        likes=8,
        user=config.api_url_prefix + api.url_path_for('get_specific_user', username='ExampleUser'),
        post=config.api_url_prefix + api.url_path_for('get_specific_post', post_id=1),
    )


api = APIRouter()
api.include_router(users_api)
api.include_router(posts_api)
api.include_router(comments_api)
