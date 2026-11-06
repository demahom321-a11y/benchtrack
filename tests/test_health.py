
def test_health_check(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}


def test_homepage_loads(client):
    response = client.get("/")

    assert response.status_code == 200
    assert "BenchTrack" in response.text
