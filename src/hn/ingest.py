import httpx
from httpx_retries import Retry, RetryTransport
import asyncio
from hn.model import User, Comment, Story, engine
from datetime import datetime, timezone
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session
from time import perf_counter
import structlog
import tenacity
import argparse
import logging

Parser = argparse.ArgumentParser(usage="python -m hn.ingest")
Parser.add_argument("--verbose", action="store_true")
Parser.add_argument("--semaphore", type=int, default=20)
args = Parser.parse_args()
retry = Retry(total=5,backoff_factor=0.5, status_forcelist=[500,502,503,504], allowed_methods=["GET", "HEAD"])
transport = RetryTransport(retry=retry)
logger = structlog.get_logger()
debug = args.verbose
semaphore = args.semaphore

def setup_logging(log_level: str = "DEBUG" if debug else "INFO"):
    logging.basicConfig(
        level=log_level,
        format="%(message)s"
    )
    logging.getLogger("httpx").setLevel(logging.WARNING)
    structlog.configure(
        processors=[
        structlog.dev.ConsoleRenderer(pad_event=0)
        ],
        wrapper_class=structlog.make_filtering_bound_logger(logging.getLevelNamesMapping()[log_level])
    )

async def fetch(url, client, sem):
    async with sem:
        r = await client.get(url)
        r.raise_for_status()
        return r.json()

async def get_story_ids(client, sem):
    storyids = await fetch(url="https://hacker-news.firebaseio.com/v0/topstories.json", client=client, sem=sem)
    return storyids

async def fetch_item(storyid, client, sem):
    itemjson = await fetch(url=f"https://hacker-news.firebaseio.com/v0/item/{storyid}.json", client=client, sem=sem)

    if itemjson is None or itemjson.get("deleted") or itemjson.get("dead"):
        return None
    
    return itemjson

async def fetch_user_profile(name: str, client, sem):
    userjson = await fetch(url=f"https://hacker-news.firebaseio.com/v0/user/{name}.json", client=client, sem=sem)
    if userjson is None:
        return None
    
    return userjson

async def get_or_fetchuser(name, users_by_name, client, sem):
    if name in users_by_name:
        return users_by_name[name]
    
    profile = await fetch_user_profile(name=name, client=client, sem=sem)
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

async def process_story(sid, client, comments, users_by_name, sem):
    log = logger.bind(story_id=sid)
    await log.ainfo("processing_story...")
    storyjson = await fetch_item(storyid=sid, client=client, sem=sem)

    if storyjson is None:
        return None
    if storyjson.get("type") != "story":
        return None
    if not storyjson.get("by"):
        return None
    
    author = await get_or_fetchuser(storyjson["by"], users_by_name=users_by_name, client=client, sem=sem)

    if author is None:
        return None

    story = Story(
            id=storyjson["id"],
            title=storyjson["title"],
            author=author,
            url=storyjson.get("url"),
            score=storyjson.get("score", 0),
            descendants_count=storyjson.get("descendants"),
            created_at=datetime.fromtimestamp(storyjson["time"], tz=timezone.utc),
        )
    
    if storyjson.get("kids"):
            await asyncio.gather(*(process_comment(
                kid_id=k,
                story_id=story.id,
                parent_comment=None,        
                users_by_name=users_by_name,
                comments=comments,
                client=client,
                sem=sem
            )for k in storyjson["kids"]), return_exceptions=True)
    
    await log.ainfo("story fetched", comment_count=len(storyjson["kids"]))
    
    return story

async def process_comment(kid_id, story_id, parent_comment, users_by_name, comments, client, sem):
    commentjson = await fetch_item(storyid=kid_id, client=client, sem=sem)
    if commentjson is None or commentjson.get("deleted") or commentjson.get("dead"):
        return None
    author = await get_or_fetchuser(commentjson.get("by"), users_by_name=users_by_name, client=client, sem=sem)
    if author is None:
        return None
    
    comment = Comment(
        id=commentjson["id"],
        author=author,
        story_id=story_id,
        parent=parent_comment,        
        html=commentjson.get("text"),
        created_at=datetime.fromtimestamp(commentjson["time"], tz=timezone.utc),
    )
    if commentjson.get("kids"):
            await asyncio.gather(*(process_comment(
                kid_id=k,
                story_id=story_id,
                parent_comment=comment,    
                users_by_name=users_by_name,
                comments=comments,
                client=client,
                sem=sem
            )for k in commentjson["kids"]), return_exceptions=True)

    comments.append(comment)

    return comment

async def ingest(n:int, client, sem):
    users_by_name = {}
    stories = []
    comments = []
    ids = (await get_story_ids(client=client, sem=sem))[:n]

    results = await asyncio.gather(*(process_story(sid=id, client=client, comments=comments, users_by_name=users_by_name, sem=sem) for id in ids), return_exceptions=True)
    for r in results:
        if r is not None and not isinstance(r, Exception):
            stories.append(r)

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

async def main():
    setup_logging()
    sem = asyncio.Semaphore(semaphore)
    async with httpx.AsyncClient(transport=transport) as client:
        users, stories, comments = await ingest(5, client=client, sem=sem)
    #save(users=users, stories=stories, comments=comments)
    await logger.ainfo("Logged", users=len(users), stories=len(stories), comments=len(comments))

if __name__ == "__main__":
    
    start = perf_counter()
    asyncio.run(main())
    end = perf_counter()
    print(end-start)
