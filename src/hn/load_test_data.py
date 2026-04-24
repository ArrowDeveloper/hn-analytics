from datetime import datetime, timezone
from hn.db import get_conn

rows = [
    ("alice", 1500, datetime(2015, 3, 1, tzinfo=timezone.utc), "about text"),
    ("bob", 200, datetime(2020, 6, 15, tzinfo=timezone.utc), None),
]
stories = [(1,"alice", "testing", 34, datetime(2020, 5, 14, tzinfo=timezone.utc)),
           (2, "bob", "helloworld", 37, datetime(2020, 3, 14, tzinfo=timezone.utc))]

comments = [(1, "alice", 1, None, datetime(2020, 3, 14, tzinfo=timezone.utc)),
             (2, "bob", 1, 1, datetime(2020, 1, 14, tzinfo=timezone.utc)),
             (3, "bob", 2, None, datetime(2020, 3, 15, tzinfo=timezone.utc)),
]
with get_conn() as conn:
    with conn.cursor() as cur:
        cur.executemany("INSERT INTO users (name, karma_score, created_at, about) VALUES (%s,%s,%s,%s)", rows)
        cur.executemany("INSERT INTO stories (id, author_name, title, score, created_at) VALUES (%s,%s,%s,%s,%s)", stories)
        cur.executemany("INSERT INTO comments (id, author_name, story_id, parent_comment, created_at) VALUES (%s,%s, %s, %s, %s)", comments)
        conn.commit()
