from typing import List

from pydantic.main import BaseModel


class User(BaseModel):
    username: str


class UserIn(User):
    password: str


class UserOut(User):
    posts: List[str] = []
    comments: List[str] = []


class Comment(BaseModel):
    content: str


class CommentIn(Comment):
    pass


class CommentOut(Comment):
    likes: int = 0
    user: str
    post: str


class Post(BaseModel):
    content: str


class PostIn(Post):
    pass


class PostOut(Post):
    likes: int = 0
    user: str
    comments: List[str] = []
