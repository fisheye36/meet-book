from typing import List, Optional

from pydantic.main import BaseModel


class User(BaseModel):
    username: str


class UserIn(User):
    password: str


class UserOut(User):
    posts: List[str] = []
    comments: List[str] = []
    self: Optional[str] = None


class Comment(BaseModel):
    content: str


class CommentIn(Comment):
    pass


class CommentOut(Comment):
    uuid: str
    timestamp: str
    likes: int = 0
    user: str
    post: str


class Post(BaseModel):
    content: str


class PostIn(Post):
    pass


class PostOut(Post):
    uuid: str
    timestamp: str
    likes: int = 0
    user: str
    comments: List[str] = []
