import os
import sys
import time

import jwt
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.config import Settings, get_settings  # noqa: E402
from app.data.fixtures import seed_competitions, seed_demo_athlete, seed_templates  # noqa: E402
from app.db import Base, get_db, make_engine  # noqa: E402
from app.main import create_app  # noqa: E402

JWT_SECRET = "test-secret-with-enough-length-for-hs256-0123456789"
SUPABASE_URL = "https://example-project.supabase.co"


def make_client(db_path, settings: Settings, client_addr=("127.0.0.1", 50000)):
    engine = make_engine(f"sqlite:///{db_path}")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    app = create_app()

    def _db():
        db = Session()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = _db
    app.dependency_overrides[get_settings] = lambda: settings
    return TestClient(app, client=client_addr), Session, engine


@pytest.fixture
def demo(tmp_path):
    s = Settings(app_mode="demo", database_url="sqlite:///x.db", ai_provider="mock")
    client, Session, engine = make_client(tmp_path / "demo.db", s)
    with Session() as db:
        seed_templates(db)
        seed_competitions(db)
    yield client, Session, tmp_path / "demo.db", s
    engine.dispose()


@pytest.fixture
def demo_athlete(demo):
    client, Session, path, s = demo
    with Session() as db:
        seed_demo_athlete(db, "demo-athlete")
    return demo


@pytest.fixture
def live(tmp_path):
    s = Settings(app_mode="live", database_url="sqlite:///x.db", supabase_url=SUPABASE_URL, supabase_jwt_secret=JWT_SECRET)
    client, Session, engine = make_client(tmp_path / "live.db", s)
    with Session() as db:
        seed_templates(db)
        seed_competitions(db)
    yield client, Session, s
    engine.dispose()


def token(sub="user-a", aud="authenticated", iss=f"{SUPABASE_URL}/auth/v1", exp_delta=3600, secret=JWT_SECRET):
    return jwt.encode({"sub": sub, "aud": aud, "iss": iss, "exp": int(time.time()) + exp_delta}, secret, algorithm="HS256")


def auth(sub="user-a", **kw):
    return {"Authorization": f"Bearer {token(sub, **kw)}"}
