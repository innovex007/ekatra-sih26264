from contextlib import contextmanager

from sqlmodel import Session, SQLModel, create_engine

from . import models  # noqa: F401  (register tables)
from .config import DATABASE_URL

_kwargs = {"connect_args": {"check_same_thread": False}} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, **_kwargs)


def init_db(drop: bool = False):
    if drop:
        SQLModel.metadata.drop_all(engine)
    SQLModel.metadata.create_all(engine)


def get_session():
    with Session(engine) as s:
        yield s


@contextmanager
def session_scope():
    with Session(engine) as s:
        yield s
