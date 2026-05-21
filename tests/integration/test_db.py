import pytest
from hn.ingest import upsert_users
from hn.model import User
from datetime import datetime
from sqlalchemy.orm import Session

@pytest.mark.integration
def test_upserts(test_dbsession):
    users= [User(name = "test1", karma_score=100, created_at=datetime.now(), about=None)]
    upsert_users(users=users, session=test_dbsession)
    changeduser = [User(name = "test1", karma_score=120, created_at=datetime.now(), about=None)]
    upsert_users(users=changeduser, session=test_dbsession)
    test_dbsession.flush()

    ruser = test_dbsession.get(User, "test1")

    assert ruser.karma_score == 120
