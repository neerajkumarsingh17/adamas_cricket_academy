import uuid

import pytest

from apps.core.middleware import REQUEST_ID_HEADER


@pytest.mark.django_db
def test_request_id_generated_when_absent(client):
    response = client.get("/api/v1/health/")

    assert REQUEST_ID_HEADER in response.headers
    assert response.headers[REQUEST_ID_HEADER]


@pytest.mark.django_db
def test_inbound_request_id_is_echoed_back(client):
    inbound = uuid.uuid4().hex

    response = client.get("/api/v1/health/", headers={"X-Request-Id": inbound})

    assert response.headers[REQUEST_ID_HEADER] == inbound
