from sqlalchemy import create_engine, Integer, String, ForeignKey, DateTime
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship, Session
import os
from dotenv import load_dotenv
from datetime import datetime, timezone

load_dotenv()

ENGINE_URL = os.environ.get("ENGINE_URL")
engine = create_engine(ENGINE_URL)

class Base(DeclarativeBase):
    pass

class User(Base):
    __tablename__ = 'users'

    name : Mapped[str] = mapped_column(String, primary_key=True)
    karma_score : Mapped[int] = mapped_column(Integer)
    created_at : Mapped[datetime] = mapped_column(DateTime(timezone=True)) 
    about : Mapped[str | None] = mapped_column(String)

    stories : Mapped[list["Story"]] = relationship(back_populates="author") 
    comments : Mapped[  list["Comment"]] = relationship(back_populates="author") 

class Story(Base):
    __tablename__ = 'stories'

    id : Mapped[int] = mapped_column(Integer, primary_key=True)
    title : Mapped[str] = mapped_column(String)
    author_name : Mapped[str | None] = mapped_column(ForeignKey("users.name"), index=True)
    url : Mapped[str | None] = mapped_column(String)
    score : Mapped[int] = mapped_column(Integer)
    created_at : Mapped[datetime] = mapped_column(DateTime(timezone=True)) 
    descendants_count : Mapped[int | None] = mapped_column(Integer)

    comments : Mapped[list["Comment"]] = relationship(back_populates="story")
    author : Mapped["User | None"] = relationship(back_populates="stories")

class Comment(Base):
    __tablename__ = 'comments'

    id : Mapped[int] = mapped_column(Integer, primary_key=True)
    author_name : Mapped[str | None] = mapped_column(ForeignKey("users.name"), index=True)
    story_id : Mapped[int] = mapped_column(ForeignKey("stories.id"), index=True)
    parent_comment : Mapped[int | None] = mapped_column(ForeignKey("comments.id"), index=True)
    html : Mapped[str | None] = mapped_column(String)
    created_at : Mapped[datetime] = mapped_column(DateTime(timezone=True))

    author : Mapped["User | None"] = relationship(back_populates="comments")
    story: Mapped["Story"] = relationship(back_populates="comments")
    parent: Mapped["Comment | None"] = relationship(
        back_populates="replies",
        remote_side=[id]
    )
    replies: Mapped[list["Comment"]] = relationship(back_populates="parent") 

def init_db():
    Base.metadata.create_all()

if __name__ == "__main__":
    init_db()
    




