from services.app_service.app import app


def test_metrics():
    client = app.test_client()
    response = client.get("/metrics")
    assert response.status_code == 200