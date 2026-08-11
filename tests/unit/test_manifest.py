from secure_cloud_platform.manifest import build_kubernetes_manifest
from secure_cloud_platform.models import Workload


def test_manifest_is_versioned_and_digest_pinned() -> None:
    image = "registry.example.test/api@sha256:" + "b" * 64
    workload = Workload(
        id="5a7e9c42-f64f-48dc-aa02-665086d3ea30",
        name="payments-api",
        image=image,
        replicas=3,
        container_port=8080,
        created_by="operator",
        version=4,
    )

    manifest = build_kubernetes_manifest(workload)

    assert manifest["metadata"]["annotations"]["scip.dev/workload-version"] == "4"
    deployment = manifest["items"][0]
    assert deployment["spec"]["replicas"] == 3
    assert deployment["spec"]["template"]["spec"]["containers"][0]["image"] == image
