from typing import List

from fastapi import APIRouter, Depends, HTTPException, Response, status
from neo4j.exceptions import ConstraintError

from backend.config import config
from backend.database import database
from backend.models import CommentIn, CommentOut, PostIn, PostOut, UserIn, UserOut
from backend.security import create_auth_token, get_logged_user
from backend.utils import uuid


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

        db_user = results['u']
        return UserOut(
            **db_user,
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
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail='User not found')

        db_user, *db_posts = nodes
        return UserOut(
            **db_user,
            posts=[config.api_url_prefix + api.url_path_for('get_specific_post', post_id=db_post['uuid'])
                   for db_post in db_posts],
            self=config.api_url_prefix + api.url_path_for('get_specific_user', username=db_user.username),
        )


@users_api.get('/users', response_model=List[UserOut])
def get_users():
    with database.session as s:
        return [UserOut(**db_user) for db_user in s.run('MATCH (u:User) RETURN u').value()]


posts_api = APIRouter(tags=['posts'])


@posts_api.post('/posts', response_model=PostOut)
def create_post(post: PostIn, user: UserOut = Depends(get_logged_user)):
    with database.session as s:
        try:
            results = s.run('MATCH (u:User) WHERE u.username = $username '
                            'CREATE (p:Post { uuid: $uuid, timestamp: timestamp(), content: $content })<-[:Posted]-(u) '
                            'RETURN p',
                            username=user.username,
                            uuid=uuid(),
                            content=post.content).single()
        except ConstraintError:
            raise HTTPException(status_code=status.HTTP_406_NOT_ACCEPTABLE, detail='Post UUID duplication') from None
        else:
            db_post = results['p']
            return PostOut(
                **db_post,
                user=config.api_url_prefix + api.url_path_for('get_specific_user', username=user.username),
                self=config.api_url_prefix + api.url_path_for('get_specific_post', post_id=db_post['uuid']),
            )


@posts_api.get('/posts/{post_id}', response_model=PostOut)
def get_specific_post(post_id: str):
    with database.session as s:
        nodes = s.run('MATCH (p:Post)<-[:Posted]-(u:User) WHERE p.uuid = $uuid RETURN p, u',
                      uuid=post_id).graph().nodes
        if not nodes:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail='Post not found')

        db_post, db_user = nodes
        return PostOut(
            **db_post,
            user=config.api_url_prefix + api.url_path_for('get_specific_user', username=db_user['username']),
            self=config.api_url_prefix + api.url_path_for('get_specific_post', post_id=db_post['uuid']),
        )


@posts_api.get('/posts', response_model=List[PostOut])
def get_posts():
    posts: List[PostOut] = []
    with database.session as s:
        for record in s.run('MATCH (p:Post)<-[:Posted]-(u:User) RETURN p, u ORDER BY p.timestamp DESC'):
            db_post = record['p']
            db_user = record['u']
            posts.append(PostOut(
                **db_post,
                user=config.api_url_prefix + api.url_path_for('get_specific_user', username=db_user['username']),
                self=config.api_url_prefix + api.url_path_for('get_specific_post', post_id=db_post['uuid']),
            ))
        return posts


comments_api = APIRouter(tags=['comments'])


@comments_api.post('/posts/{post_id}/comments', response_model=CommentOut)
def create_comment(post_id: str, comment: CommentIn, user: UserOut = Depends(get_logged_user)):
    with database.session as s:
        try:
            results = s.run('MATCH (u:User), (p:Post) WHERE u.username = $username AND p.uuid = $post_id '
                            'CREATE (u)-[c:Commented { uuid: $uuid, timestamp: timestamp(), content: $content }]->(p) '
                            'RETURN c',
                            username=user.username,
                            post_id=post_id,
                            uuid=uuid(),
                            content=comment.content).single()
        except ConstraintError:
            raise HTTPException(status_code=status.HTTP_406_NOT_ACCEPTABLE, detail='Comment UUID duplication') from None
        else:
            if not results:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Post not found')

            db_comment = results['c']
            return CommentOut(
                **db_comment,
                user=config.api_url_prefix + api.url_path_for('get_specific_user', username=user.username),
                post=config.api_url_prefix + api.url_path_for('get_specific_post', post_id=post_id),
                self=config.api_url_prefix + api.url_path_for('get_specific_comment', comment_id=db_comment['uuid']),
            )


@comments_api.get('/comments/{comment_id}', response_model=CommentOut)
def get_specific_comment(comment_id: str):
    return CommentOut(
        content='ExampleCommentContent',
        likes=8,
        user=config.api_url_prefix + api.url_path_for('get_specific_user', username='ExampleUser'),
        post=config.api_url_prefix + api.url_path_for('get_specific_post', post_id='1'),
    )


# TODO: get_comments_for_post

api = APIRouter()
api.include_router(users_api)
api.include_router(posts_api)
api.include_router(comments_api)
