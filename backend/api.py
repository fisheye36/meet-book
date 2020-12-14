from typing import List

from fastapi import APIRouter, Depends, HTTPException, Response, status
from neo4j.exceptions import ConstraintError

from backend.config import config
from backend.database import database
from backend.models import CommentIn, CommentOut, PostIn, PostOut, UserIn, UserOut
from backend.security import create_auth_token, get_logged_user
from backend.utils import timestamp, uuid


users_api = APIRouter(tags=['users'])


@users_api.post('/login', response_model=UserOut, tags=['authentication'])
def login(response: Response, user: UserIn):
    with database.session as s:
        results = s.run('MATCH (u:User) WHERE u.username = $username AND u.password = $password RETURN u',
                        username=user.username, password=user.password).single()
        if not results:
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail='Wrong credentials')

        token = create_auth_token(user)
        response.set_cookie(
            key=config.auth_token_name,
            value=token,
            max_age=config.cookie_max_age_seconds,
        )

        response_user = results['u']
        return UserOut(
            **response_user,
            self=config.api_url_prefix + api.url_path_for('get_specific_user', username=user.username),
        )


@users_api.post('/users', response_model=UserOut)
def create_user(user: UserIn):
    with database.session as s:
        try:
            s.run('CREATE (u:User { username: $username, password: $password })', user.dict())
        except ConstraintError:
            raise HTTPException(status.HTTP_406_NOT_ACCEPTABLE, detail='User already exists') from None
        else:
            return UserOut(
                **user.dict(),
                self=config.api_url_prefix + api.url_path_for('get_specific_user', username=user.username)
            )


@users_api.get('/users/{username}', response_model=UserOut)
def get_specific_user(username: str):
    with database.session as s:
        nodes = s.run('MATCH (u:User)-->(p:Post) WHERE u.username = $username RETURN u, p',
                      username=username).graph().nodes
        if not nodes:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail='Not found')

        user, *posts = nodes
        return UserOut(
            **user,
            posts=[config.api_url_prefix + api.url_path_for('get_specific_post', post_id=post['uuid'])
                   for post in posts],
            self=config.api_url_prefix + api.url_path_for('get_specific_user', username=user.username),
        )


@users_api.get('/users', response_model=List[UserOut])
def get_users():
    with database.session as s:
        users: List[UserOut] = []
        for user in s.run('MATCH (u:User) RETURN u').value():
            users.append(UserOut(**user))
        return users


posts_api = APIRouter(tags=['posts'])


@posts_api.post('/posts', response_model=PostOut)
def create_post(post: PostIn, user: UserOut = Depends(get_logged_user)):
    with database.session as s:
        results = s.run('MATCH (u:User) WHERE u.username = $username '
                        'CREATE (p:Post { uuid: $uuid, timestamp: $timestamp, content: $content })<-[:Posted]-(u) '
                        'RETURN p',
                        username=user.username,
                        uuid=uuid(),
                        timestamp=timestamp(),
                        content=post.content).single()

        post = results['p']
        return PostOut(
            **post,
            user=config.api_url_prefix + api.url_path_for('get_specific_user', username=user.username)
        )


@posts_api.get('/posts/{post_id}', response_model=PostOut)
def get_specific_post(post_id: str):
    return PostOut(
        content='ExamplePost',
        likes=4,
        user=config.api_url_prefix + api.url_path_for('get_specific_user', username='ExampleUser'),
        comments=[
            config.api_url_prefix + api.url_path_for('get_specific_comment', comment_id='1'),
            config.api_url_prefix + api.url_path_for('get_specific_comment', comment_id='2'),
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
                config.api_url_prefix + api.url_path_for('get_specific_comment', comment_id='1'),
                config.api_url_prefix + api.url_path_for('get_specific_comment', comment_id='2'),
            ],
        ),
    ]


comments_api = APIRouter(tags=['comments'])


@comments_api.post('/posts/{post_id}/comments', response_model=CommentOut)
def create_comment(post_id: str, comment: CommentIn):
    return CommentOut(
        **comment.dict(),
        user=config.api_url_prefix + api.url_path_for('get_specific_user', username='ExampleUser'),
        post=config.api_url_prefix + api.url_path_for('get_specific_post', post_id=post_id),
    )


@comments_api.get('/comments/{comment_id}', response_model=CommentOut)
def get_specific_comment(comment_id: str):
    return CommentOut(
        content='ExampleCommentContent',
        likes=8,
        user=config.api_url_prefix + api.url_path_for('get_specific_user', username='ExampleUser'),
        post=config.api_url_prefix + api.url_path_for('get_specific_post', post_id='1'),
    )


api = APIRouter()
api.include_router(users_api)
api.include_router(posts_api)
api.include_router(comments_api)
