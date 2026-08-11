from __future__ import annotations

from fastapi.testclient import TestClient

from tests.conftest import (
    ADMIN_PASSWORD,
    OPERATOR_PASSWORD,
    VIEWER_PASSWORD,
    auth,
    token_for,
)

IMAGE = "registry.example.test/payments@sha256:" + "a" * 64


def test_health_metrics_and_security_headers(client: TestClient) -> None:
    live = client.get("/health/live", headers={"X-Request-ID": "demo-request-1"})
    ready = client.get("/health/ready")
    metrics = client.get("/metrics")

    assert live.status_code == 200
    assert ready.json() == {"status": "ready"}
    assert "scip_http_requests_total" in metrics.text
    assert live.headers["x-request-id"] == "demo-request-1"
    assert live.headers["x-content-type-options"] == "nosniff"
    assert live.headers["x-frame-options"] == "DENY"


def test_role_boundaries_and_optimistic_concurrency(client: TestClient) -> None:
    viewer = token_for(client, "viewer", VIEWER_PASSWORD)
    operator = token_for(client, "operator", OPERATOR_PASSWORD)
    admin = token_for(client, "admin", ADMIN_PASSWORD)

    denied = client.post(
        "/v1/workloads",
        headers=auth(viewer),
        json={"name": "payments-api", "image": IMAGE, "replicas": 2},
    )
    assert denied.status_code == 403

    created = client.post(
        "/v1/workloads",
        headers=auth(operator),
        json={"name": "payments-api", "image": IMAGE, "replicas": 2},
    )
    assert created.status_code == 201, created.text
    workload = created.json()
    assert workload["version"] == 1
    assert (
        client.post(
            "/v1/workloads",
            headers=auth(operator),
            json={"name": "payments-api", "image": IMAGE, "replicas": 2},
        ).status_code
        == 409
    )

    manifest = client.get(
        f"/v1/workloads/{workload['id']}/manifest",
        headers=auth(viewer),
    )
    assert manifest.status_code == 200
    deployment = manifest.json()["items"][0]
    assert deployment["spec"]["template"]["spec"]["automountServiceAccountToken"] is False
    assert deployment["spec"]["template"]["spec"]["containers"][0]["image"] == IMAGE
    assert deployment["spec"]["template"]["spec"]["containers"][0]["securityContext"] == {
        "allowPrivilegeEscalation": False,
        "readOnlyRootFilesystem": True,
        "capabilities": {"drop": ["ALL"]},
    }

    visible = client.get("/v1/workloads", headers=auth(viewer))
    assert [item["name"] for item in visible.json()] == ["payments-api"]

    scaled = client.patch(
        f"/v1/workloads/{workload['id']}/scale",
        headers=auth(operator),
        json={"replicas": 4, "expected_version": 1},
    )
    assert scaled.status_code == 200, scaled.text
    assert scaled.json()["replicas"] == 4
    assert scaled.json()["version"] == 2

    stale = client.patch(
        f"/v1/workloads/{workload['id']}/scale",
        headers=auth(operator),
        json={"replicas": 5, "expected_version": 1},
    )
    assert stale.status_code == 409
    assert (
        client.patch(
            "/v1/workloads/00000000-0000-0000-0000-000000000000/scale",
            headers=auth(operator),
            json={"replicas": 2, "expected_version": 1},
        ).status_code
        == 404
    )

    assert (
        client.delete(f"/v1/workloads/{workload['id']}", headers=auth(operator)).status_code == 403
    )
    assert client.delete(f"/v1/workloads/{workload['id']}", headers=auth(admin)).status_code == 204
    assert client.get(f"/v1/workloads/{workload['id']}", headers=auth(viewer)).status_code == 404


def test_admin_creates_narrow_service_identity_and_reads_audit(client: TestClient) -> None:
    admin = token_for(client, "admin", ADMIN_PASSWORD)
    user = {
        "username": "release-viewer",
        "password": "Release-Viewer-Passphrase-2026!",
        "role": "viewer",
    }
    assert client.post("/v1/users", headers=auth(admin), json=user).status_code == 201
    assert client.post("/v1/users", headers=auth(admin), json=user).status_code == 409
    assert token_for(client, user["username"], user["password"])

    excessive = client.post(
        "/v1/service-accounts",
        headers=auth(admin),
        json={"name": "excessive-reader", "role": "viewer", "scopes": ["audit:read"]},
    )
    assert excessive.status_code == 409

    created = client.post(
        "/v1/service-accounts",
        headers=auth(admin),
        json={
            "name": "deployment-reader",
            "role": "viewer",
            "scopes": ["workloads:read"],
        },
    )
    assert created.status_code == 201, created.text
    identity = created.json()
    assert identity["client_secret"]

    service_token = client.post(
        "/v1/auth/service-token",
        json={
            "client_id": identity["client_id"],
            "client_secret": identity["client_secret"],
        },
    )
    assert service_token.status_code == 200
    assert (
        client.post(
            "/v1/auth/service-token",
            json={"client_id": identity["client_id"], "client_secret": "x" * 32},
        ).status_code
        == 401
    )
    service_headers = auth(service_token.json()["access_token"])
    assert client.get("/v1/workloads", headers=service_headers).status_code == 200
    assert (
        client.post(
            "/v1/workloads",
            headers=service_headers,
            json={"name": "forbidden-write", "image": IMAGE},
        ).status_code
        == 403
    )

    audit = client.get("/v1/audit-events", headers=auth(admin))
    assert audit.status_code == 200
    assert "identity.service_account.create" in {event["action"] for event in audit.json()}


def test_credentials_and_input_fail_closed(client: TestClient) -> None:
    invalid_login = client.post(
        "/v1/auth/token",
        data={"username": "admin", "password": "wrong"},
    )
    assert invalid_login.status_code == 401

    operator = token_for(client, "operator", OPERATOR_PASSWORD)
    mutable_image = client.post(
        "/v1/workloads",
        headers=auth(operator),
        json={"name": "mutable", "image": "registry.example.test/app:latest"},
    )
    assert mutable_image.status_code == 422
