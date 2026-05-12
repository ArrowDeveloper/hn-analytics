# hn-analytics

A ETL pipeline that ingests Hacker News stories and comments into Postgres,
runs analytical SQL queries via SQLAlchemy, and exports reports as CSV.

Built as a learning project to practice production-shaped Python: ORM modeling
with SQLAlchemy 2.0, idempotent upserts, recursive data fetching, and analytical
queries (joins, aggregations, window functions).

## What it does

The program fetches the top N stories from Hacker News Firebase API (`https://hacker-news.firebaseio.com/v0/topstories.json`), also recursively loops through each story's comment tree, collecting comments and storing the users who posted them. It upserts users, stories and comments into a Postgres Database, and it also runs features like analytical queries over the ingested data (top stories, top authors by average score, hourly post volume, top story per author, etc.) and exporting the result to CSV reports using pandas.

## Tech stack

- Python 3.14
- PostgreSQL
- SQLAlchemy 2.0 (ORM with Mapped / mapped_column / DeclarativeBase)
- psycopg v3
- pandas
- requests

## Project layout

    src/hn/
        model.py     SQLAlchemy ORM models (User, Story, Comment) + engine
        ingest.py    HN API fetch, recursive comment walk, idempotent upsert
        query.py     Analytical queries (joins, aggregates, window functions)
        report.py    CSV report generation via pandas
    pyproject.toml
    .env.example     Template for required environment variables

## Setup

1. Install Postgres locally and create a database and user:

       CREATE DATABASE hn_analytics;
       CREATE USER hn_user WITH PASSWORD 'your_password';
       GRANT ALL PRIVILEGES ON DATABASE hn_analytics TO hn_user;

2. Clone and install:

       git clone https://github.com/ArrowDeveloper/hn-analytics.git
       cd hn-analytics
       python -m venv .venv
       source .venv/bin/activate    # on Windows: .venv\Scripts\activate
       pip install -e .

3. Copy `.env.example` to `.env` and fill in the connection string:

       ENGINE_URL=postgresql+psycopg://hn_user:your_password@localhost/hn_analytics

4. Initialize the schema:

       python -m hn.model

## Usage

Ingest the top 50 stories and their comment trees:

    python -m hn.ingest 50

Verbose mode for debug logging:

    python -m hn.ingest 50 --verbose

Run analytical queries (currently only the functions are created and needs manual tinkering for use):

    python -m hn.query

Generate the average-score-per-author CSV report:

    python -m hn.report

Output is saved in `reports/`.

## Performance

Uses concurrency with httpx and asyncio, with a 60% improvement of speed with Sephamore set to 20 and upto 85% with no limit set.
Sequential ingest for 1 story yielded a time of approx. 20 seconds whereas current setup yeilds 8 seconds with limit and ~3-5 seconds without limit.

## Schema

Three tables with foreign-key relationships:

- `users` primary key on `name`. Stores karma, about text, and account
  creation time.
- `stories` primary key on `id`. Foreign key to `users.name`.
- `comments` primary key on `id`. Foreign keys to `users.name`, `stories.id`,
  and a self-referential `parent_comment` for reply chains.

Timestamps are stored as `TIMESTAMP WITH TIME ZONE`, 
converted from HN's Unix-second integers.

## Notes on implementation

- Upserts use Postgres's `INSERT ... ON CONFLICT DO UPDATE` via SQLAlchemy's `pg_insert`.
- Comment fetching is currently sequential and is the main bottleneck for
  large N. Concurrent ingestion (asyncio + httpx) is planned.
- HTTP retries use `requests` + `urllib3.Retry` with backoff on
  5xx responses.
- Logging is configured at the entry point; modules use
  `logging.getLogger(__name__)` and emit at INFO/DEBUG levels.

## Limitations / future work

- No automated tests yet. Pytest will be added later on.
- Reports module currently has one report function; more functions will be added.
