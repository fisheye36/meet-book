from typing import List

from pydantic.main import BaseModel


class User(BaseModel):
    username: str


class UserIn(User):
    password: str


class UserOut(User):
    posts: List[str] = []
    comments: List[str] = []
    url: str


class Comment(BaseModel):
    content: str


class CommentIn(Comment):
    pass


class CommentOut(Comment):
    uuid: str
    timestamp: str
    author: str
    post: str
    url: str


class Post(BaseModel):
    content: str


class PostIn(Post):
    pass


class PostOut(Post):
    uuid: str
    timestamp: str
    author: str
    comments: List[str] = []
    url: str
