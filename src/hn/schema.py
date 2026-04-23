from hn.db import get_conn

def create_tables():
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS users (
                        name TEXT PRIMARY KEY,
                        karma_score INTEGER NOT NULL,
                        created_at TIMESTAMPTZ NOT NULL,
                        about TEXT)
                        """)
            conn.commit()
            cur.execute("""
                CREATE TABLE IF NOT EXISTS stories(
                        id INTEGER PRIMARY KEY,
                        title TEXT NOT NULL,
                        author_name TEXT,
                        url TEXT,
                        score INTEGER NOT NULL,
                        descendants_count INTEGER,
                        created_at TIMESTAMPTZ NOT NULL,
                        FOREIGN KEY (author_name) REFERENCES users(name) ON DELETE RESTRICT
                        )
                        """)
            conn.commit()
            cur.execute("""
                CREATE TABLE IF NOT EXISTS comments(
                        id INTEGER PRIMARY KEY,
                        author_name TEXT,
                        story_id INTEGER NOT NULL,
                        parent_comment INTEGER,
                        html TEXT,
                        created_at TIMESTAMPTZ NOT NULL,
                        FOREIGN KEY (author_name) REFERENCES users(name) ON DELETE RESTRICT,
                        FOREIGN KEY (story_id) REFERENCES stories(id) ON DELETE RESTRICT,
                        FOREIGN KEY (parent_comment) REFERENCES comments(id) ON DELETE RESTRICT
                        )
                        """)
            conn.commit()
            cur.execute("CREATE INDEX IF NOT EXISTS idx_cmt_author_name ON comments(author_name)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_story_id ON comments(story_id)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_parentcmt_id ON comments(parent_comment)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_story_author_name ON stories(author_name)")
            conn.commit()

if __name__ == "__main__":
    create_tables()