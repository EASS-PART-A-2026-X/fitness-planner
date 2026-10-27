from pathlib import Path

from sqlmodel import Session, SQLModel, create_engine

data_dir = Path(__file__).resolve().parents[2] / "data"
data_dir.mkdir(parents=True, exist_ok=True)
sqlite_url = f"sqlite:///{data_dir / 'database.db'}"

engine = create_engine(sqlite_url, connect_args={"check_same_thread": False})


def create_db_and_tables() -> None:
    SQLModel.metadata.create_all(engine)


def get_session():
    with Session(engine) as session:
        yield session
