import pytest

def test_health(test_client):
    response = test_client.get("/health")
    result = response.json()
    assert result["status"] == "ok"
    
@pytest.mark.integration
def test_get_story(test_client):
    response = test_client.get("/stories/47921248")
    result = response.json()
    assert response.status_code == 200
    assert result["author_name"] == "helsinkiandrew"
    assert result["id"] == 47921248
    assert result["score"] == 121

def test_get_story_not_found(test_client):
    response = test_client.get("/stories/124515222")
    
    assert response.status_code == 404  
