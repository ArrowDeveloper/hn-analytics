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

def get_data(n: int):
    r = nsession.get("https://hacker-news.firebaseio.com/v0/topstories.json")
    storyids = r.json()
    firstnstories = storyids[:n]
    datalist = []

    for storyid in firstnstories:
        story = nsession.get(f"https://hacker-news.firebaseio.com/v0/item/{storyid}.json")
        storyjson = story.json()

        if storyjson is None or storyjson.get("deleted") or storyjson.get("dead"):
            continue
        if storyjson.get("type") != "story":
            continue

        author = storyjson.get("by")
        authordata = nsession.get(f"https://hacker-news.firebaseio.com/v0/user/{author}.json")
        authorjson = authordata.json()

        about = authorjson.get("about")
        karma_score = authorjson.get("karma")
        author_created_at = authorjson.get("created")

        desecendants = storyjson.get("descendants")
        kids = storyjson.get("kids")
        score = storyjson.get("score")
        title = storyjson.get("title")
        story_created_at = storyjson.get("time")
        text = storyjson.get("text")
        url = storyjson.get("url")

        datalist.append({"author": author,"storyid": storyid,"url": url, "about": about, "karma_score": karma_score, "author_created_at": author_created_at,"desecendants": desecendants, "kids": kids, "score": score, "title": title, "story_created_at": story_created_at, "text": text})

    return datalist
        

def save_data_to_db(datalist):
    with Session(engine) as session:
        for data in datalist:    
            user = User(name=data.get("author"), karma_score=data.get("karma_score"), about=data.get("about"),created_at=datetime.fromtimestamp(data.get("author_created_at"), tz=timezone.utc))
            story = Story(id=data.get("storyid"), title=data.get("title"), author_name=data.get("author"), score=data.get("score"), descendants_count=data.get("desecendants"), created_at=datetime.fromtimestamp(data.get("story_created_at"), tz=timezone.utc))
            session.add_all([user,story])
        session.commit()

datalist = get_data(5)

if __name__ == "__main__":
    save_data_to_db(datalist=datalist)