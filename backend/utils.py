from datetime import datetime
from uuid import uuid4


DATE_FORMAT = '%d/%m/%Y %H:%M:%S'


def timestamp() -> str:
    return datetime.now().strftime(DATE_FORMAT)


def uuid() -> str:
    return str(uuid4())
