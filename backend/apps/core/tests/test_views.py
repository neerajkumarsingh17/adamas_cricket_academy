import pytest


@pytest.mark.django_db
def test_health_reports_database_and_redis_ok(client):
    response = client.get("/api/v1/health/")

    assert response.status_code == 200
    assert response.json() == {"database": "ok", "redis": "ok"}
