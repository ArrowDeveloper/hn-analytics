import requests 
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from hn.model import User, Comment, Story, engine
from sqlalchemy.orm import Session
from datetime import datetime, timezone
from sqlalchemy.dialects.postgresql import insert as pg_insert
import logging
import argparse

logger = logging.getLogger(__name__)
retry_policy = Retry(total=3,backoff_factor=0.5,status_forcelist=[500,502,503,504],allowed_methods=["GET", "HEAD"])
adapter = HTTPAdapter(max_retries=retry_policy)

def MakeSession():
    session = requests.Session()
    session.mount("https://", adapter=adapter)
    session.mount("http://", adapter=adapter)
    session.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    })

    return session

nsession = MakeSession()

def get_story_ids():
    r = nsession.get("https://hacker-news.firebaseio.com/v0/topstories.json")
    storyids = r.json()
    return storyids

def fetch_item(storyid):
    item = nsession.get(f"https://hacker-news.firebaseio.com/v0/item/{storyid}.json")
    itemjson = item.json()

    if itemjson is None or itemjson.get("deleted") or itemjson.get("dead"):
        return None
    
    return itemjson

def fetch_user_profile(name: str):
    user = nsession.get(f"https://hacker-news.firebaseio.com/v0/user/{name}.json")
    userjson = user.json()

    if userjson is None:
        return None

    return userjson

def get_or_fetchuser(name, users_by_name):
    if name in users_by_name:
        return users_by_name[name]
    
    profile = fetch_user_profile(name=name)
    if profile is None:
        return None
    
    user = User(
        name=name,
        karma_score=profile.get("karma", 0),
        about=profile.get("about"),
        created_at=datetime.fromtimestamp(profile.get("created"), tz=timezone.utc)
    )
    users_by_name[name] = user
    return user

def recursive_comments(kid_ids,story_id,parent_comment,users_by_name, comments):
    for kid_id in kid_ids:
        comment = nsession.get(f"https://hacker-news.firebaseio.com/v0/item/{kid_id}.json")
        commentjson = comment.json()

        if commentjson is None or commentjson.get("deleted") or commentjson.get("dead"):
            continue

        author = get_or_fetchuser(commentjson.get("by"), users_by_name=users_by_name)

        if author is None:
            continue

        comment = Comment(
            id=commentjson["id"],
            author=author,
            story_id=story_id,
            parent=parent_comment,        
            html=commentjson.get("text"),
            created_at=datetime.fromtimestamp(commentjson["time"], tz=timezone.utc),
        )
        comments.append(comment)
        if commentjson.get("kids"):
            recursive_comments(
                kid_ids=commentjson["kids"],
                story_id=story_id,
                parent_comment=comment,    
                users_by_name=users_by_name,
                comments=comments,
            )
        logger.debug(f"Fetched comment id {kid_id}")

def ingest(n:int):
    users_by_name = {}
    stories = []
    comments = []

    for storyid in get_story_ids()[:n]:
        storyjson = fetch_item(storyid=storyid)
        if storyjson is None:
            continue
        if storyjson.get("type") != "story":
            continue
        if not storyjson.get("by"):
            continue

        author = get_or_fetchuser(storyjson["by"], users_by_name)
        logger.debug(f"Fetched User {storyjson.get("by")}")
        if author is None:
            continue

        story = Story(
            id=storyjson["id"],
            title=storyjson["title"],
            author=author,
            url=storyjson.get("url"),
            score=storyjson.get("score", 0),
            descendants_count=storyjson.get("descendants"),
            created_at=datetime.fromtimestamp(storyjson["time"], tz=timezone.utc),
        )
        stories.append(story)
        logger.debug(f"Fetched Story {storyjson["id"]}")
        if storyjson.get("kids"):
            recursive_comments(
                kid_ids=storyjson["kids"],
                story_id=story.id,
                parent_comment=None,        
                users_by_name=users_by_name,
                comments=comments,
            )
        

    return list(users_by_name.values()), stories, comments

def user_to_dict(user):
    return {
        "name": user.name,
        "karma_score": user.karma_score,
        "about": user.about,
        "created_at": user.created_at,
    }
def story_to_dict(story):
    return {
        "id": story.id,
        "title": story.title,
        "author_name": story.author.name, 
        "url": story.url,
        "score": story.score,
        "descendants_count": story.descendants_count,
        "created_at": story.created_at,
    }

def comment_to_dict(comment):
    return {
        "id": comment.id,
        "author_name": comment.author.name,
        "story_id": comment.story_id,
        "parent_comment": comment.parent.id if comment.parent else None,
        "html": comment.html,
        "created_at": comment.created_at,
    }

def upsert_users(session,users):
    rows = [user_to_dict(u) for u in users]
    stmt = pg_insert(User).values(rows)
    stmt = stmt.on_conflict_do_update(
        index_elements=["name"],
        set_={
            "about": stmt.excluded.about,
            "karma_score": stmt.excluded.karma_score
        })

    session.execute(stmt)

def upsert_stories(session, stories):
    rows = [story_to_dict(s) for s in stories]
    stmt = pg_insert(Story).values(rows)
    stmt = stmt.on_conflict_do_update(index_elements=["id"],
        set_={
            "score": stmt.excluded.score,
            "descendants_count": stmt.excluded.descendants_count,
            "title": stmt.excluded.title,
            "url": stmt.excluded.url
        })
    
    session.execute(stmt)

def upsert_comments(session, comments):
    rows = [comment_to_dict(c) for c in comments]
    stmt = pg_insert(Comment).values(rows)
    stmt = stmt.on_conflict_do_update(index_elements=["id"],
        set_={
            "html": stmt.excluded.html,
        })
    
    session.execute(stmt)

def save(users, stories, comments):
    with Session(engine) as session:
        upsert_users(session=session, users=users)
        upsert_stories(session=session, stories=stories)
        upsert_comments(session=session,comments=comments)
        session.commit()

if __name__ == "__main__":
    Parser = argparse.ArgumentParser(usage="python -m hn.ingest <number of stories>")

    Parser.add_argument("--verbose", action="store_true")
    Parser.add_argument("no_of_ingestion", type=int)

    args = Parser.parse_args()
    n = args.no_of_ingestion
    level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    users, stories, comments = ingest(n)
    logger.info("Ingested %d users, %d stories, %d comments", len(users), len(stories), len(comments))
    save(users=users, stories=stories, comments=comments)
    logger.info("Completed.")

