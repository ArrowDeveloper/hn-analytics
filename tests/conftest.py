import pytest
from fastapi.testclient import TestClient
from hn.api import app
from dotenv import load_dotenv
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from hn.model import Base

load_dotenv()

TEST_URL = os.environ.get("TEST_DB_URL")

@pytest.fixture(scope="session")
def test_engine():
    test_engine = create_engine(TEST_URL)
    Base.metadata.create_all(test_engine)
    yield test_engine
    Base.metadata.drop_all(test_engine)
    test_engine.dispose()

@pytest.fixture
def test_dbsession(test_engine):
    with Session(test_engine) as session:
        beggining = session.begin()
        yield session
        beggining.rollback()

@pytest.fixture(scope="session")
def test_client():
    return TestClient(app)