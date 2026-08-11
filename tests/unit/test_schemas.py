import pytest
from pydantic import ValidationError

from secure_cloud_platform.schemas import WorkloadCreate


def test_workload_requires_kubernetes_name_and_immutable_image() -> None:
    valid = WorkloadCreate(
        name="payments-api",
        image="registry.example.test/payments@sha256:" + "a" * 64,
    )
    assert valid.replicas == 1

    with pytest.raises(ValidationError):
        WorkloadCreate(name="Payments_API", image=valid.image)
    with pytest.raises(ValidationError):
        WorkloadCreate(name="payments-api", image="registry.example.test/payments:latest")
