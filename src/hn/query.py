from hn.model import Story, Comment, User, engine
from sqlalchemy import select, func, extract
from sqlalchemy.orm import Session

def get_top_stories(session):
    stmt = select(Story).order_by(Story.score.desc()).limit(10)
    return session.scalars(stmt).all()

def get_authors_avg_stmt(min_stories: int = 1):
    stmt = (select(Story.author_name, func.avg(Story.score).label("avg_score"))
            .where(Story.score > 10)
            .group_by(Story.author_name)
            .having(func.count() >= min_stories)
    )
    return stmt

def get_authors_by_avg_score(session):
    stmt = get_authors_avg_stmt()
    return session.execute(stmt).all()

def stories_with_comments_count(session, limit: int=10):
    stmt = (select(Story.title, func.count(Comment.id).label("n_comments")).outerjoin(Story.comments).group_by(Story.id, Story.title).having(func.count() >= limit).order_by(func.count(Comment.id).desc()))
    return session.execute(stmt).all()

def active_commenters(session, limit: int=10):
    stmt = (select(User.name, func.count(Comment.id).label("n_comments")).outerjoin(User.comments).group_by(User.name).order_by(func.count(Comment.id).desc()).limit(limit=limit))
    return session.execute(stmt).all()

def commenters_who_also_post(session):
    posters = select(User.name).join(User.stories).distinct().subquery()
    commenters = select(User.name).join(User.comments).distinct().subquery()
    stmt = select(posters.c.name).join(commenters, posters.c.name == commenters.c.name)
    return session.scalars(stmt).all()

def highest_score_story(session):
    story = select(Story.author_name, Story.score, func.row_number().over(partition_by=Story.author_name, order_by=Story.score.desc()).label("rn")).subquery()
    stmt = select(story).where(story.c.rn == 1)

    return session.execute(stmt).all()

def group_by_time(session):
    hour_expr = extract('hour', Story.created_at).label("hour")
    stmt = select(hour_expr, func.count().label("n")).group_by(hour_expr).order_by(hour_expr)

    return session.execute(stmt).all()

if __name__ == "__main__":
    with Session(engine) as session:
        stories = get_top_stories(session=session)
        avg_scores = get_authors_by_avg_score(session=session)
        comments_count = stories_with_comments_count(session=session)
        commenters = active_commenters(session=session)
        posters = commenters_who_also_post(session = session)
        highest_scores =  highest_score_story(session=session)
        groupbyhour = group_by_time(session=session)
