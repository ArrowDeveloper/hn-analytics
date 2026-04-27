import requests 
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from hn.model import User, Comment, Story, engine
from sqlalchemy.orm import Session
from datetime import datetime, timezone

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

        if storyjson.get("kids"):
            recursive_comments(
                kid_ids=storyjson["kids"],
                story_id=story.id,
                parent_comment=None,        
                users_by_name=users_by_name,
                comments=comments,
            )

    return list(users_by_name.values()), stories, comments

def save(users, stories, comments):
    with Session(engine) as session:
        session.add_all(users + stories + comments)
        session.commit()

if __name__ == "__main__":
    users, stories, comments = ingest(1)
    print(f"Ingesting {len(users)} users, {len(stories)} stories, {len(comments)} comments.")
    save(users=users, stories=stories, comments=comments)
    print("Done.")

