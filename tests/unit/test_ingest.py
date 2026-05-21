import pytest
import respx
import httpx
from hn.model import User
from hn.ingest import user_to_dict, fetch_item
from datetime import datetime
import asyncio
from unittest.mock import patch

@respx.mock
async def test_fetch_item():
    respx.get("https://hacker-news.firebaseio.com/v0/item/123.json").mock(
        return_value=httpx.Response(200, json={"id": 123, "type": "story", "title": "Test"})
    )
    sem = asyncio.Semaphore(1)
    async with httpx.AsyncClient() as client:
        result = await fetch_item(123, client=client, sem=sem)

    assert result["id"] == 123
    assert result["type"] == "story"
    assert result["title"] == "Test"

@respx.mock 
@patch('time.sleep')
async def test_retries(mock_sleep):
    route = respx.get("https://hacker-news.firebaseio.com/v0/item/12.json")

    route.side_effect = [
        httpx.Response(500),
        httpx.Response(500),
        httpx.Response(200, json={"id": 12, "type": "story", "title": "test"}),
    ]

    sem = asyncio.Semaphore(1)
    async with httpx.AsyncClient() as client:
        result = await fetch_item(12, client=client, sem=sem)

    assert result["id"] == 12
    assert result["type"] == "story"
    assert result["title"] == "test"

def test_user_to_dict():
    now = datetime.now()
    formatted = now.strftime("%Y-%m-%d")
    user = User(name="test", karma_score=100, about=None, created_at=formatted)
    result = user_to_dict(user)
    assert result["name"] == "test"
    assert result["karma_score"] == 100
    assert result["about"] == None
    assert result["created_at"] == formatted