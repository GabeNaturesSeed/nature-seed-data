"""SQLAlchemy engine and session factory."""

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from naturesseed_pipeline.config import settings

engine = create_engine(settings.database_url, echo=False)
SessionLocal = sessionmaker(bind=engine)


def get_session() -> Generator[Session, None, None]:
    """Yield a database session, closing on exit."""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
