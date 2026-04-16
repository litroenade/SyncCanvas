"""User repositories."""

from sqlmodel import Session, select

from src.persistence.db.models.users import User


def get_user_by_username(session: Session, username: str) -> User | None:
    statement = select(User).where(User.username == username)
    return session.exec(statement).first()
