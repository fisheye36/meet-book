from typing import List

from fastapi import APIRouter, Depends, HTTPException, Response, status
from neo4j import Record, Session
from neo4j.exceptions import ConstraintError

from backend.config import config
from backend.database import database
from backend.models import CommentIn, CommentOut, Message, PostIn, PostOut, UserIn, UserOut
from backend.security import create_auth_token, get_logged_user
from backend.utils import uuid


users_api = APIRouter(tags=['users'])


@users_api.post('/login', response_model=UserOut, tags=['authentication'])
def login(response: Response, user: UserIn):
    with database.session as s:
        results = s.run(
            'MATCH (u:User { username: $username, password: $password } )'
            'RETURN u',
            username=user.username,
            password=user.password,
        ).single()
        if not results:
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail='Wrong credentials')

        token = create_auth_token(user)
        response.set_cookie(
            key=config.auth_token_name,
            value=token,
            max_age=config.cookie_max_age_seconds,
        )

        return _get_user_from_db(s, user.username)


@users_api.get('/logout', response_model=Message, tags=['authentication'])
def logout(response: Response):
    response.delete_cookie(key=config.auth_token_name)
    return Message(message='Logged out')


@users_api.post('/users', response_model=UserOut)
def create_user(response: Response, user: UserIn):
    with database.session as s:
        try:
            s.run('CREATE (u:User { username: $username, password: $password })', user.dict())
        except ConstraintError:
            raise HTTPException(status.HTTP_406_NOT_ACCEPTABLE, detail='User already exists') from None
        else:
            response.status_code = status.HTTP_201_CREATED
            return UserOut(
                **user.dict(),
                url=config.api_url_prefix + api.url_path_for('get_specific_user', username=user.username)
            )


@users_api.get('/users/{username}', response_model=UserOut)
def get_specific_user(username: str):
    with database.session as s:
        return _get_user_from_db(s, username)


@users_api.get('/users', response_model=List[UserOut])
def get_users():
    with database.session as s:
        return _get_users_from_db(s)


def _get_user_from_db(s: Session, username: str) -> UserOut:
    record = s.run(
        'MATCH (u:User {username: $username}) '
        'WITH u, [(u)-[:Posted]->(p:Post) | p] as posts, [(u)-[c:Commented]->(:Post) | c] as comments '
        'return u, posts, comments',
        username=username,
    ).single()
    if not record:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail='User not found')

    return _build_user_from_db_record(record)


def _get_users_from_db(s: Session) -> List[UserOut]:
    results = s.run(
        'MATCH (u:User) '
        'WITH u, [(u)-[:Posted]->(p:Post) | p] as posts, [(u)-[c:Commented]->(:Post) | c] as comments '
        'return u, posts, comments',
    )

    return [_build_user_from_db_record(record) for record in results]


def _build_user_from_db_record(record: Record) -> UserOut:
    db_user = record['u']
    db_posts = sorted(record['posts'], key=lambda p: p['timestamp'])
    db_comments = sorted(record['comments'], key=lambda c: c['timestamp'])

    return UserOut(
        **db_user,
        posts=[config.api_url_prefix + api.url_path_for('get_specific_post', post_id=db_post['uuid'])
               for db_post in db_posts],
        comments=[config.api_url_prefix + api.url_path_for('get_specific_comment', comment_id=db_comment['uuid'])
                  for db_comment in db_comments],
        url=config.api_url_prefix + api.url_path_for('get_specific_user', username=db_user['username']),
    )


posts_api = APIRouter(tags=['posts'])


@posts_api.post('/posts', response_model=PostOut)
def create_post(response: Response, post: PostIn, user: UserOut = Depends(get_logged_user)):
    with database.session as s:
        try:
            results = s.run(
                'MATCH (u:User { username: $username }) '
                'CREATE (p:Post { uuid: $uuid, timestamp: timestamp(), content: $content })<-[:Posted]-(u) '
                'RETURN p',
                username=user.username,
                uuid=uuid(),
                content=post.content
            ).single()
        except ConstraintError:
            raise HTTPException(status_code=status.HTTP_406_NOT_ACCEPTABLE, detail='Post UUID duplication') from None
        else:
            response.status_code = status.HTTP_201_CREATED
            db_post = results['p']
            return PostOut(
                **db_post,
                author=config.api_url_prefix + api.url_path_for('get_specific_user', username=user.username),
                url=config.api_url_prefix + api.url_path_for('get_specific_post', post_id=db_post['uuid']),
            )


@posts_api.get('/posts/{post_id}', response_model=PostOut)
def get_specific_post(post_id: str):
    with database.session as s:
        return _get_post_from_db(s, post_id)


@posts_api.get('/posts', response_model=List[PostOut])
def get_posts():
    with database.session as s:
        return _get_posts_from_db(s)


def _get_post_from_db(s: Session, post_id: str) -> PostOut:
    record = s.run(
        'MATCH (p:Post { uuid: $uuid })<-[:Posted]-(u:User) '
        'WITH p, u, [(p)<-[c:Commented]-(:User) | c] as comments '
        'RETURN p, u, comments',
        uuid=post_id,
    ).single()
    if not record:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail='Post not found')

    return _build_post_from_db_record(record)


def _get_posts_from_db(s: Session) -> List[PostOut]:
    results = s.run(
        'MATCH (p:Post)<-[:Posted]-(u:User) '
        'WITH p, u, [(p)<-[c:Commented]-(:User) | c] as comments '
        'RETURN p, u, comments',
    )

    return sorted([_build_post_from_db_record(record) for record in results], key=lambda p: p.timestamp, reverse=True)


def _build_post_from_db_record(record: Record) -> PostOut:
    db_post = record['p']
    db_user = record['u']
    db_comments = sorted(record['comments'], key=lambda c: c['timestamp'])

    return PostOut(
        **db_post,
        author=config.api_url_prefix + api.url_path_for('get_specific_user', username=db_user['username']),
        comments=[config.api_url_prefix + api.url_path_for('get_specific_comment', comment_id=db_comment['uuid'])
                  for db_comment in db_comments],
        url=config.api_url_prefix + api.url_path_for('get_specific_post', post_id=db_post['uuid']),
    )


comments_api = APIRouter(tags=['comments'])


@comments_api.post('/posts/{post_id}/comments', response_model=CommentOut)
def create_comment(response: Response, post_id: str, comment: CommentIn, user: UserOut = Depends(get_logged_user)):
    with database.session as s:
        if not s.run('MATCH (p:Post { uuid: $uuid }) RETURN p', uuid=post_id).single():
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail='Post not found')

        results = s.run(
            'MATCH (u:User { username: $username }), (p:Post { uuid: $post_id } ) '
            'CREATE (u)-[c:Commented { uuid: $uuid, timestamp: timestamp(), content: $content }]->(p) '
            'RETURN c',
            username=user.username,
            post_id=post_id,
            uuid=uuid(),
            content=comment.content
        ).single()

        response.status_code = status.HTTP_201_CREATED
        db_comment = results['c']
        return CommentOut(
            **db_comment,
            author=config.api_url_prefix + api.url_path_for('get_specific_user', username=user.username),
            post=config.api_url_prefix + api.url_path_for('get_specific_post', post_id=post_id),
            url=config.api_url_prefix + api.url_path_for('get_specific_comment', comment_id=db_comment['uuid']),
        )


@comments_api.get('/comments/{comment_id}', response_model=CommentOut)
def get_specific_comment(comment_id: str):
    with database.session as s:
        return _get_comment_from_db(s, comment_id)


@comments_api.get('/comments', response_model=List[CommentOut])
def get_comments():
    with database.session as s:
        return _get_comments_from_db(s)


@comments_api.get('/posts/{post_id}/comments', response_model=List[CommentOut])
def get_post_comments(post_id: str):
    with database.session as s:
        return _get_post_comments_from_db(s, post_id)


def _get_comment_from_db(s: Session, comment_id: str) -> CommentOut:
    record = s.run(
        'MATCH (u:User)-[c:Commented { uuid: $uuid }]->(p:Post) '
        'RETURN c, u, p',
        uuid=comment_id,
    ).single()
    if not record:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail='Comment not found')

    return _build_comment_from_db_record(record)


def _get_comments_from_db(s: Session) -> List[CommentOut]:
    results = s.run(
        'MATCH (u:User)-[c:Commented]->(p:Post) '
        'RETURN c, u, p',
    )

    return sorted([_build_comment_from_db_record(record) for record in results], key=lambda c: c.timestamp)


def _get_post_comments_from_db(s: Session, post_id: str) -> List[CommentOut]:
    if not s.run('MATCH (p:Post { uuid: $uuid }) RETURN p', uuid=post_id).single():
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail='Post not found')

    results = s.run(
        'MATCH (u:User)-[c:Commented]->(p:Post { uuid: $uuid }) '
        'RETURN c, u, p',
        uuid=post_id,
    )

    return sorted([_build_comment_from_db_record(record) for record in results], key=lambda c: c.timestamp)


def _build_comment_from_db_record(record: Record) -> CommentOut:
    db_comment = record['c']
    db_user = record['u']
    db_post = record['p']

    return CommentOut(
        **db_comment,
        author=config.api_url_prefix + api.url_path_for('get_specific_user', username=db_user['username']),
        post=config.api_url_prefix + api.url_path_for('get_specific_post', post_id=db_post['uuid']),
        url=config.api_url_prefix + api.url_path_for('get_specific_comment', comment_id=db_comment['uuid']),
    )


api = APIRouter()
api.include_router(users_api)
api.include_router(posts_api)
api.include_router(comments_api)
