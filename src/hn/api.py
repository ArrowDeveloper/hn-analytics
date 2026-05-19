from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import select
from hn.model import engine, User, Story, Comment
from pydantic import BaseModel
from datetime import datetime
from hn.ingest import ingest
from httpx import AsyncClient
from asyncio import Semaphore
app = FastAPI()

class StoryResponse(BaseModel):
    id: int
    title: str
    score: int
    url: str | None
    descendants_count: int | None
    author_name: str
    created_at : datetime

    model_config = {"from_attributes": True}

class CommentResponse(BaseModel):
    id : int
    author_name: str | None
    story_id : int
    parent_comment : int | None
    html : str | None
    created_at : datetime

    model_config = {"from_attributes": True}

class UserResponse(BaseModel):
    name : str
    karma_score : int
    created_at : datetime
    about : str | None

    model_config = {"from_attributes": True}

class IngestResponse(BaseModel):
    userscount : int
    storiescount : int
    commentscount : int

    model_config = {"from_attributes": True}

class IngestRequest(BaseModel):
    semaphore : int
    limit : int
    model_config = {"from_attributes": True}

def get_db():
    with Session(engine) as session:
        yield session

@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/stories/{story_id}", response_model=StoryResponse)
def list_stories(story_id:int, limit: int = 10, offset: int = 0, db: Session = Depends(get_db)):
    story = db.get(Story, story_id)
    if story is None:
        raise HTTPException(status_code=404, detail="Story not found")
    return story

@app.get("/comments/{comment_id}", response_model=CommentResponse)
def list_comments(comment_id: int, db: Session = Depends(get_db)):
    comment = db.get(Comment, comment_id)
    if comment is None:
        raise HTTPException(status_code=404, detail="Comment not found")
    return comment

@app.get("/users/{username}", response_model=UserResponse)
def list_comments(username: str, db: Session = Depends(get_db)):
    user = db.get(User, username)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return user

@app.post("/ingest", response_model=IngestResponse)
async def ingeststuff(req: IngestRequest):
    sem = Semaphore(req.semaphore)
    async with AsyncClient() as client:
        users, stories, comments, errors = await ingest(n=req.limit, sem=sem, client=client)
    return {"userscount": len(users), "storiescount": len(stories), "commentscount": len(comments)}
