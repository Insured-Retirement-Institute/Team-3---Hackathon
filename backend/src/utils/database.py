from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./test.db")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    use_json_store = os.getenv("USE_JSON_STORE", "true").lower() in {"1", "true", "yes"}
    if use_json_store:
        yield None
        return

    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()