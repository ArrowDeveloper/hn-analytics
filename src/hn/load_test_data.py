from hn.model import User, Comment, Story, engine
from sqlalchemy.orm import Session
from datetime import datetime, timezone

with Session(engine) as session:
    testboi = User(name="testboi", karma_score=1000, created_at=datetime.now(timezone.utc))
    testgurl = User(name="testgurl", karma_score=1300, created_at=datetime.now(timezone.utc))
    story1 = Story(id=1, title="test", author=testboi, score=10, created_at=datetime.now(timezone.utc))
    story2 = Story(id=2, title="test2", author=testgurl, score=20, created_at=datetime.now(timezone.utc))
    comment1 = Comment(id=1, author=testboi, story = story1, created_at=datetime.now(timezone.utc))
    comment2 = Comment(id=2, author=testgurl, story=story1, parent=comment1, created_at=datetime.now(timezone.utc))
    session.add_all([testboi,testgurl,story1,comment1,comment2])
    session.commit()

