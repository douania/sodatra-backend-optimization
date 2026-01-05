from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

_engine = None
_SessionLocal = None

def init_db(database_url: str):
    global _engine, _SessionLocal
    if not database_url:
        print("WARNING: DATABASE_URL not set, Case Files features disabled")
        return
    _engine = create_engine(database_url, pool_pre_ping=True, future=True)
    _SessionLocal = sessionmaker(bind=_engine, autoflush=False, autocommit=False, future=True)
    print("Database initialized successfully")

def get_session():
    if _SessionLocal is None:
        raise RuntimeError("DB not initialized - DATABASE_URL may be missing")
    return _SessionLocal()

def is_db_available():
    return _SessionLocal is not None
